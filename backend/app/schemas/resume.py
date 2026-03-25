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


class ResumeResponse(BaseModel):
    """Full resume details returned by GET /resume/."""

    id: int
    user_id: int
    parsed_skills: dict
    word_count: int
    skill_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class SkillsResponse(BaseModel):
    """Skills-only payload returned by GET /resume/skills."""

    skills: dict
    flat_skills: list[str]
    total_count: int
