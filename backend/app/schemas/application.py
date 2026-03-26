from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    company_name: str = Field(..., min_length=1)
    job_title: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=50, max_length=20_000)
    notes: Optional[str] = None
    applied_date: Optional[date] = None
    job_url: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: Literal["saved", "applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]
    notes: Optional[str] = None


class ApplicationNotesUpdate(BaseModel):
    notes: str


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MatchResult(BaseModel):
    fit_score: float
    fit_score_pct: int
    fit_label: str
    semantic_score: float
    skill_overlap_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    total_jd_skills: int
    total_matched: int
    total_missing: int

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    """Light response — used for list views."""
    id: int
    user_id: int
    company_name: str
    job_title: str
    status: str
    fit_score_pct: Optional[int]
    fit_label: Optional[str]
    applied_date: Optional[date]
    job_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailResponse(ApplicationResponse):
    """Full response — used for detail/single-item views."""
    job_description: str
    jd_skills: Optional[dict]
    matched_skills: Optional[list[str]]
    missing_skills: Optional[list[str]]
    semantic_score: Optional[float]
    skill_overlap_score: Optional[float]
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)
