from typing import Optional

from pydantic import BaseModel, ConfigDict


class WeeklyCount(BaseModel):
    week: str
    count: int

    model_config = ConfigDict(from_attributes=True)


class SkillGap(BaseModel):
    skill: str
    count: int

    model_config = ConfigDict(from_attributes=True)


class StatusBreakdown(BaseModel):
    saved: int = 0
    applied: int = 0
    phone_screen: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0
    withdrawn: int = 0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsSummaryResponse(BaseModel):
    total_applications: int
    by_status: StatusBreakdown
    avg_fit_score_pct: Optional[float]
    highest_fit_score_pct: Optional[int]
    lowest_fit_score_pct: Optional[int]
    analyzed_count: int
    pending_count: int
    weekly_applications: list[WeeklyCount]
    top_missing_skills: list[SkillGap]
    interview_rate: float
    offer_rate: float

    model_config = ConfigDict(from_attributes=True)
