"""
Pydantic schemas for resume endpoints.

SkillsDict          — typed shape of extracted skills (used inside responses)
ResumeTextUpload    — request body for plain-text upload
ResumeUploadResponse — returned by POST /resume/upload
ResumeResponse      — returned by GET  /resume/
SkillsResponse      — returned by GET  /resume/skills
ResumeDeleteResponse — returned by DELETE /resume/
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base / shared models
# ---------------------------------------------------------------------------

class SkillsDict(BaseModel):
    """
    Typed container for categorised skills extracted from a resume.

    WHY typed instead of plain dict:
      A plain dict gives no IDE autocompletion and allows any shape.
      Typing each category makes the contract explicit — callers know exactly
      which keys exist and that values are always lists of strings.
    """

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ResumeTextUpload(BaseModel):
    """Request body for uploading resume as plain text (no PDF)."""

    text: str = Field(
        ...,
        min_length=100,
        max_length=50_000,
        description="Plain text content of the resume (100–50 000 characters).",
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ResumeUploadResponse(BaseModel):
    """Returned by POST /resume/upload after successful processing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    parsed_skills: SkillsDict
    word_count: int
    skill_count: int
    embedding_id: Optional[str] = None
    uploaded_at: datetime
    message: str


class ResumeResponse(BaseModel):
    """Returned by GET /resume/ — full resume details for the current user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    parsed_skills: SkillsDict
    word_count: int
    skill_count: int
    uploaded_at: datetime


class SkillsResponse(BaseModel):
    """Returned by GET /resume/skills — skills only, no raw text."""

    skills: SkillsDict
    flat_skills: list[str]
    total_count: int


class ResumeDeleteResponse(BaseModel):
    """Returned by DELETE /resume/."""

    message: str
    deleted_id: str
