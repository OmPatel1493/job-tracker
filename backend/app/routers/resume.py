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
from app.services.skill_extractor import (
    extract_skills_with_gemini,
    extract_skills_with_regex,
)
from app.utils.exceptions import PDFParseError, ResumeValidationError, VectorServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])

# 10 MB hard cap - well above any real resume; protects against accidental large uploads
MAX_PDF_BYTES = 10 * 1024 * 1024

# PDF magic bytes - first 4 bytes of every valid PDF file
_PDF_MAGIC = b"%PDF"


# ---------------------------------------------------------------------------
# Extended upload response (adds ai_status without touching schemas file)
# ---------------------------------------------------------------------------

class ResumeUploadWithAiStatus(ResumeUploadResponse):
    """
    Extends the base upload response with an AI processing status field.

    ai_status values:
      "full"        - Gemini processed and returned skills
      "fallback"    - Gemini failed; regex extraction was used instead
      "unavailable" - both Gemini and regex failed (skills will be empty)
    """
    ai_status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_pdf_magic(data: bytes) -> bool:
    return data[:4] == _PDF_MAGIC


async def _extract_skills_with_status(text: str) -> tuple[dict, str]:
    """
    Extract skills and return (skills_dict, ai_status).

    Detects whether Gemini or regex was actually used by comparing results:
    - When Gemini quota is exceeded, extract_skills_with_gemini() falls back
      to extract_skills_with_regex() internally and returns the same result.
    - If the outputs differ, Gemini produced a richer result → "full".
    - If the outputs are identical, the internal regex fallback was used → "fallback".
    - If an unexpected exception occurs → "unavailable" with empty skills.
    """
    try:
        # Regex is deterministic - run it first as our baseline
        regex_result = extract_skills_with_regex(text)
        # Gemini call: handles its own fallback internally, never raises
        gemini_result = await extract_skills_with_gemini(text)

        if gemini_result != regex_result:
            return gemini_result, "full"
        else:
            # Identical output means Gemini fell back to regex internally
            return regex_result, "fallback"

    except Exception as exc:
        logger.error("Skill extraction failed entirely: %s", exc)
        return {}, "unavailable"


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
# POST /resume/parse - PDF → plain text (utility, no DB write)
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=ParsedResumeResponse)
async def parse_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
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
# POST /resume/extract-skills - text → categorised skills (utility, no DB write)
# ---------------------------------------------------------------------------

@router.post("/extract-skills", response_model=ExtractSkillsResponse)
async def extract_resume_skills(
    body: ExtractSkillsRequest,
    current_user: User = Depends(get_current_user),
):
    skills, _ = await _extract_skills_with_status(body.text)
    return ExtractSkillsResponse(skills=skills)


# ---------------------------------------------------------------------------
# POST /resume/upload - full pipeline: parse → validate → extract → embed → save
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=ResumeUploadWithAiStatus, status_code=status.HTTP_200_OK)
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
      1. Validate file size + magic bytes (PDF path only).
      2. Extract text from PDF bytes or clean plain text input.
      3. Validate that the text is long enough to be a real resume.
      4. Extract categorised skills via Gemini (falls back to regex silently).
      5. Create or update the resume record in the database.
      6. Attempt Pinecone embedding - if Pinecone fails, set embedding_id=None
         and continue. Never return 503 for external AI/vector store failures.

    Only returns 503 if PostgreSQL is unreachable (handled by FastAPI/SQLAlchemy).
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
    # 3. Extract skills - Gemini with regex fallback, tracks which was used
    # ------------------------------------------------------------------
    parsed_skills, ai_status = await _extract_skills_with_status(resume_text)

    # ------------------------------------------------------------------
    # 4. Create or update DB record (flush to get id before Pinecone)
    # ------------------------------------------------------------------
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
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
    # 5. Upsert Pinecone embedding - failure is non-fatal
    #    A resume without an embedding still works for display and skill
    #    gap analysis; only semantic similarity search is degraded.
    # ------------------------------------------------------------------
    embedding_id: Optional[str] = None
    try:
        embedding_id = vector_service.upsert_resume_embedding(
            user_id=str(current_user.id),
            resume_id=str(resume_record.id),
            text=resume_text,
        )
    except (VectorServiceError, RuntimeError, Exception) as exc:
        logger.warning(
            "Pinecone upsert failed for user %s (resume %s) - "
            "proceeding without embedding: %s",
            current_user.id,
            resume_record.id,
            exc,
        )
        embedding_id = None

    resume_record.embedding_id = embedding_id
    await db.commit()
    await db.refresh(resume_record)

    skills = resume_record.parsed_skills or {}
    skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))

    return ResumeUploadWithAiStatus(
        id=resume_record.id,
        user_id=resume_record.user_id,
        parsed_skills=skills,
        word_count=resume_record.word_count,
        skill_count=skill_count,
        embedding_id=resume_record.embedding_id,
        uploaded_at=resume_record.updated_at,
        message="Resume uploaded and processed successfully.",
        ai_status=ai_status,
    )


# ---------------------------------------------------------------------------
# GET /resume/me - fetch current user's resume
# ---------------------------------------------------------------------------

@router.get("/me", response_model=ResumeResponse)
async def get_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated user's stored resume.

    Route is /resume/me (not /resume/) to match the REST convention used
    by the frontend and avoid ambiguity with collection routes.
    user_id is int - queried directly with ==.
    """
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
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
# GET /resume/skills - skills dict + flat list only
# ---------------------------------------------------------------------------

@router.get("/skills", response_model=SkillsResponse)
async def get_resume_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
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
# DELETE /resume/me - remove resume record + Pinecone vector
# ---------------------------------------------------------------------------

@router.delete("/me", response_model=ResumeDeleteResponse)
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the user's resume from the database and Pinecone.

    Pinecone deletion failure is non-fatal - DB record is still removed.
    """
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
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
                "Could not delete Pinecone vector '%s' for user %s - "
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
