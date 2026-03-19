"""
Resume upload + parse router.

WHY separate router: resume operations are distinct from auth and job
applications; keeps each router focused on one resource.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
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
