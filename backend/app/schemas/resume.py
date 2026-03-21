"""
Pydantic schemas for resume endpoints.

ResumeUploadResponse  — returned by POST /api/resume/upload
ResumeStatusResponse  — returned by GET  /api/resume/status  (future)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    """Full response after a successful resume upload and processing."""

    id: int
    user_id: int
    parsed_skills: dict
    word_count: int
    embedding_id: Optional[str]
    uploaded_at: datetime
    message: str

    model_config = {"from_attributes": True}


class ResumeStatusResponse(BaseModel):
    """Lightweight check — does the user have a resume on file?"""

    has_resume: bool
    resume_id: Optional[str]
    uploaded_at: Optional[datetime]
