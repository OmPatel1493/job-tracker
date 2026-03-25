"""
Resume upload + parse router.

WHY separate router: resume operations are distinct from auth and job
applications; keeps each router focused on one resource.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import (
    ResumeDeleteResponse,
    ResumeResponse,
    ResumeUploadResponse,
    SkillsResponse,
)
from app.services import pdf_service, skill_extractor, vector_service
from app.services.pdf_service import extract_text_from_bytes
from app.services.skill_extractor import extract_skills
from app.utils.exceptions import PDFParseError, ResumeValidationError, VectorServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])

# 10 MB hard cap — well above any real resume; protects against accidental large uploads
MAX_PDF_BYTES = 10 * 1024 * 1024

# PDF magic bytes — first 4 bytes of every valid PDF file
_PDF_MAGIC = b"%PDF"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_pdf_magic(data: bytes) -> bool:
    """
    Return True if the file starts with the PDF magic bytes.

    WHY magic bytes instead of (only) file extension:
        A user can rename any file to ".pdf". Checking the actual binary
        signature ensures we only feed real PDFs to pdfplumber.
    """
    return data[:4] == _PDF_MAGIC


# ---------------------------------------------------------------------------
# Inline schemas (parse / extract-skills are utility endpoints, not persisted)
# ---------------------------------------------------------------------------

class ParsedResumeResponse(BaseModel):
    filename: str
    char_count: int
    text: str


class ExtractSkillsRequest(BaseModel):
    text: str


class ExtractSkillsResponse(BaseModel):
    skills: dict[str, list[str]]


# ---------------------------------------------------------------------------
# POST /resume/parse — PDF → plain text (utility, no DB write)
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=ParsedResumeResponse)
async def parse_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF resume and return its extracted plain text.

    WHY this endpoint exists: downstream AI features need the resume as
    plain text. Parsing here keeps AI services free from raw PDF bytes.
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
            detail="File exceeds the 10 MB limit.",
        )

    if not _verify_pdf_magic(pdf_bytes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File does not appear to be a valid PDF.",
        )

    try:
        text = extract_text_from_bytes(pdf_bytes)
    except PDFParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        )
    except ResumeValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        )

    return ParsedResumeResponse(
        filename=file.filename or "resume.pdf",
        char_count=len(text),
        text=text,
    )


# ---------------------------------------------------------------------------
# POST /resume/extract-skills — text → categorised skills (utility, no DB write)
# ---------------------------------------------------------------------------

@router.post("/extract-skills", response_model=ExtractSkillsResponse)
async def extract_resume_skills(
    body: ExtractSkillsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Given plain resume text (from /resume/parse), return categorised skills
    extracted by Gemini (with regex fallback).

    WHY separate from /parse: the client may want to parse once and call
    extract-skills multiple times, or skip extraction entirely.
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
      1. Validate file size + magic bytes.
      2. Extract text from PDF bytes or clean plain text input.
      3. Validate that the text is long enough to be a real resume.
      4. Extract categorised skills via Gemini (falls back to regex).
      5. Create or update the resume record in the database.
      6. Upsert embedding in Pinecone.
         If Pinecone fails: delete the just-saved DB record and return 503.

    WHY upsert not insert:
      A user has one active resume at a time. Re-uploading should silently
      overwrite the previous version rather than creating duplicate rows.

    WHY flush before Pinecone call:
      flush() writes the row and assigns its auto-increment id without
      committing. That id is used as the Pinecone vector_id so both
      stores stay in sync.

    WHY delete DB record if Pinecone fails:
      A resume without an embedding cannot be used for AI matching. Rather
      than leaving a half-broken record, we roll back the whole operation
      and return 503 so the client can retry later.
    """
    # ------------------------------------------------------------------
    # 1. Resolve and validate input
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
                detail="File exceeds the 10 MB limit.",
            )

        if not _verify_pdf_magic(pdf_bytes):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File does not appear to be a valid PDF.",
            )

        try:
            resume_text = pdf_service.extract_text_from_pdf(pdf_bytes)
        except PDFParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=exc.detail,
            )
        except ResumeValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.detail,
            )

    elif text is not None:
        resume_text = pdf_service.extract_text_from_plain(text)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a PDF file or resume text.",
        )

    # ------------------------------------------------------------------
    # 2. Validate resume text content
    # ------------------------------------------------------------------
    is_valid, reason = pdf_service.validate_resume_text(resume_text)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resume validation failed: {reason}",
        )

    word_count = pdf_service.get_word_count(resume_text)

    # ------------------------------------------------------------------
    # 3. Extract skills via Gemini (with regex fallback — never raises)
    # ------------------------------------------------------------------
    parsed_skills = await skill_extractor.extract_skills(resume_text)

    # ------------------------------------------------------------------
    # 4. Create or update DB record (flush to get id before Pinecone)
    # ------------------------------------------------------------------
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    is_new_record = existing is None

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
    # 5. Upsert embedding in Pinecone
    #    On failure: delete the DB record (new) or leave old data intact
    #    (update) and return 503.
    # ------------------------------------------------------------------
    try:
        embedding_id = vector_service.upsert_resume_embedding(
            user_id=str(current_user.id),
            resume_id=str(resume_record.id),
            text=resume_text,
        )
        resume_record.embedding_id = embedding_id
    except (VectorServiceError, RuntimeError) as exc:
        await db.rollback()
        if is_new_record:
            logger.error(
                "Pinecone upsert failed for new resume (user %s) — DB record rolled back: %s",
                current_user.id,
                exc,
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Resume was processed but could not be saved to the vector store. "
                "Please try again later."
            ),
        )

    await db.commit()
    await db.refresh(resume_record)

    skills = resume_record.parsed_skills or {}
    skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))

    return ResumeUploadResponse(
        id=resume_record.id,
        user_id=resume_record.user_id,
        parsed_skills=skills,
        word_count=resume_record.word_count,
        skill_count=skill_count,
        embedding_id=resume_record.embedding_id,
        uploaded_at=resume_record.updated_at,
        message="Resume uploaded and processed successfully.",
    )


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

@router.delete("/", response_model=ResumeDeleteResponse)
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the user's resume from the database and Pinecone.

    WHY vector deletion is non-fatal:
      If Pinecone delete fails, the DB record is still removed. The stale
      vector is logged and can be cleaned up later. Blocking the user from
      deleting their own resume because of a vector store hiccup is worse
      than the orphaned vector.
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
        success = vector_service.delete_resume_embedding(resume.embedding_id)
        if not success:
            logger.warning(
                "Could not delete Pinecone vector '%s' for user %s — "
                "proceeding with DB delete anyway.",
                resume.embedding_id,
                current_user.id,
            )

    await db.delete(resume)
    await db.commit()

    return ResumeDeleteResponse(
        message="Resume deleted successfully.",
        deleted_id=deleted_id,
    )
