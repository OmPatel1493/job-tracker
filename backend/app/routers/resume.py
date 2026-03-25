"""
Resume upload + parse router.

WHY separate router: resume operations are distinct from auth and job
applications; keeps each router focused on one resource.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeResponse, ResumeUploadResponse, SkillsResponse
from app.services import pdf_service, skill_extractor, vector_service
from app.services.pdf_service import extract_text_from_bytes
from app.services.skill_extractor import extract_skills

router = APIRouter(prefix="/resume", tags=["Resume"])

# 5 MB upload cap — resumes are small; protects the server from large uploads
MAX_PDF_BYTES = 5 * 1024 * 1024


class ParsedResumeResponse(BaseModel):
    filename: str
    char_count: int
    text: str


class ExtractSkillsRequest(BaseModel):
    text: str


class ExtractSkillsResponse(BaseModel):
    skills: dict[str, list[str]]


@router.post("/parse", response_model=ParsedResumeResponse)
async def parse_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF resume and return its extracted plain text.

    WHY this endpoint exists: downstream AI features (Day 9+) need the
    resume as plain text to embed and match against job descriptions.
    Parsing happens here so the AI service never has to touch raw PDF bytes.
    """
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted.",
        )

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 5 MB limit.",
        )

    try:
        text = extract_text_from_bytes(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ParsedResumeResponse(
        filename=file.filename or "resume.pdf",
        char_count=len(text),
        text=text,
    )


@router.post("/extract-skills", response_model=ExtractSkillsResponse)
async def extract_resume_skills(
    body: ExtractSkillsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Given plain resume text (from /resume/parse), return categorised skills
    extracted by gpt-4o-mini.

    WHY separate from /parse: the client may want to parse once and call
    extract-skills multiple times (e.g. after editing the text), or skip
    extraction entirely. Keeping them separate avoids re-parsing the PDF
    on every AI call.
    """
    try:
        skills = await extract_skills(body.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return ExtractSkillsResponse(skills=skills)


# ---------------------------------------------------------------------------
# POST /resume/upload — full pipeline: parse → validate → extract → embed → save
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_200_OK)
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full resume upload and processing pipeline.

    Accepts either a PDF file (multipart) or plain text (form field).
    Steps:
      1. Extract text from PDF bytes or clean plain text input.
      2. Validate that the text is long enough to be a real resume.
      3. Extract categorised skills via Gemini (falls back to regex).
      4. Upsert the resume embedding into Pinecone.
      5. Create or update the resume record in the database.

    WHY upsert not insert:
      A user has one active resume at a time. Re-uploading should silently
      overwrite the previous version rather than creating duplicate rows.

    WHY flush before Pinecone call:
      flush() writes the new row to the DB and assigns its auto-increment id
      without committing the transaction. This id is used as the Pinecone
      vector_id so the two stores stay in sync. If Pinecone fails, the
      transaction is still committed (embedding_id stays None) — the resume
      is saved and can be re-embedded later.
    """
    # ------------------------------------------------------------------
    # 1. Resolve text from file or form field
    # ------------------------------------------------------------------
    if file is not None:
        filename = file.filename or ""
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only .pdf files are accepted.",
            )

        pdf_bytes = await file.read()
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds the 5 MB limit.",
            )

        try:
            resume_text = pdf_service.extract_text_from_pdf(pdf_bytes)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

    elif text is not None:
        resume_text = pdf_service.extract_text_from_plain(text)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a PDF file or resume text.",
        )

    # ------------------------------------------------------------------
    # 2. Validate resume text
    # ------------------------------------------------------------------
    is_valid, reason = pdf_service.validate_resume_text(resume_text)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resume validation failed: {reason}",
        )

    word_count = pdf_service.get_word_count(resume_text)

    # ------------------------------------------------------------------
    # 3. Extract skills via Gemini (with regex fallback)
    # ------------------------------------------------------------------
    parsed_skills = await skill_extractor.extract_skills(resume_text)

    # ------------------------------------------------------------------
    # 4. Create or update the DB record (flush to get id before Pinecone)
    # ------------------------------------------------------------------
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.raw_text = resume_text
        existing.parsed_skills = parsed_skills
        existing.word_count = word_count
        resume_record = existing
    else:
        resume_record = Resume(
            user_id=current_user.id,
            raw_text=resume_text,
            parsed_skills=parsed_skills,
            word_count=word_count,
        )
        db.add(resume_record)

    await db.flush()  # assigns resume_record.id without committing

    # ------------------------------------------------------------------
    # 5. Upsert embedding in Pinecone (non-fatal if unavailable)
    # ------------------------------------------------------------------
    try:
        embedding_id = vector_service.upsert_resume_embedding(
            user_id=str(current_user.id),
            resume_id=str(resume_record.id),
            text=resume_text,
        )
        resume_record.embedding_id = embedding_id
    except RuntimeError:
        # Vector store unavailable — save the record anyway, embed later
        resume_record.embedding_id = None

    await db.commit()
    await db.refresh(resume_record)

    return ResumeUploadResponse(
        id=resume_record.id,
        user_id=resume_record.user_id,
        parsed_skills=resume_record.parsed_skills or {},
        word_count=resume_record.word_count,
        embedding_id=resume_record.embedding_id,
        uploaded_at=resume_record.updated_at,
        message="Resume uploaded and processed successfully.",
    )
<<<<<<< HEAD


# ---------------------------------------------------------------------------
# GET /resume/ — fetch current user's resume
# ---------------------------------------------------------------------------

@router.get("/", response_model=ResumeResponse)
async def get_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated user's stored resume.

    WHY word_count is recalculated here:
      The stored word_count may be 0 on older records created before the
      field was added. Recalculating from raw_text ensures an accurate value.
    """
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume uploaded yet.",
        )

    skills = resume.parsed_skills or {}
    skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))
    word_count = resume.word_count or len((resume.raw_text or "").split())

    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        parsed_skills=skills,
        word_count=word_count,
        skill_count=skill_count,
        uploaded_at=resume.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /resume/skills — skills dict + flat list only
# ---------------------------------------------------------------------------

@router.get("/skills", response_model=SkillsResponse)
async def get_resume_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return only the skills from the user's resume.

    WHY a dedicated endpoint:
      Downstream features (job matching, skill-gap UI) only need the skills
      dict — not the full raw text. Keeping this response small reduces
      payload size and avoids sending sensitive resume text unnecessarily.
    """
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume uploaded yet.",
        )

    skills = resume.parsed_skills or {}
    flat_skills = skill_extractor.flatten_skills(skills)

    return SkillsResponse(
        skills=skills,
        flat_skills=flat_skills,
        total_count=len(flat_skills),
    )


# ---------------------------------------------------------------------------
# DELETE /resume/ — remove resume record + Pinecone vector
# ---------------------------------------------------------------------------

@router.delete("/")
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the user's resume from the database and Pinecone.

    WHY vector deletion is attempted first:
      If the DB delete succeeds but Pinecone still holds the vector, the
      orphaned vector would pollute future similarity queries. Deleting from
      Pinecone first (non-fatal on failure) minimises that risk.
    """
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found to delete.",
        )

    deleted_id = str(resume.id)

    if resume.embedding_id:
        vector_service.delete_resume_embedding(resume.embedding_id)

    await db.delete(resume)
    await db.commit()

    return {"message": "Resume deleted successfully.", "deleted_id": deleted_id}
