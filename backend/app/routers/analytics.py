"""
Analytics router.

  GET /analytics/summary - aggregated stats for the current user's applications

WHY Python-side aggregation for weekly counts and skill gaps:
    Weekly bucketing by ISO week and flattening JSON skill lists are not
    trivially expressible in portable SQL. The result sets are small
    (at most a few hundred rows per user), so fetching and grouping in
    Python is simpler and fast enough.

WHY fill missing weeks with count 0:
    The frontend chart needs a continuous 8-week series. Gaps in the
    data would cause chart libraries to skip weeks or mis-align bars.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.job_application import JobApplication
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    SkillGap,
    StatusBreakdown,
    WeeklyCount,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a full analytics summary for the current user.

    Runs five queries:
      1. Status counts + totals
      2. Fit score aggregates (avg / max / min) and analyzed/pending counts
      3. Weekly application counts for the last 8 weeks
      4. Top 10 most common missing skills across all applications
      5. Interview rate and offer rate as percentages
    """
    user_filter = JobApplication.user_id == current_user.id

    # ------------------------------------------------------------------
    # Query 1 - Status counts
    # ------------------------------------------------------------------
    status_rows = await db.execute(
        select(JobApplication.status, func.count().label("n"))
        .where(user_filter)
        .group_by(JobApplication.status)
    )
    status_counts: dict[str, int] = {row.status: row.n for row in status_rows}
    total_applications = sum(status_counts.values())

    by_status = StatusBreakdown(
        saved=status_counts.get("saved", 0),
        applied=status_counts.get("applied", 0),
        phone_screen=status_counts.get("phone_screen", 0),
        interview=status_counts.get("interview", 0),
        offer=status_counts.get("offer", 0),
        rejected=status_counts.get("rejected", 0),
        withdrawn=status_counts.get("withdrawn", 0),
    )

    # ------------------------------------------------------------------
    # Query 2 - Fit score stats
    # ------------------------------------------------------------------
    fit_agg = await db.execute(
        select(
            func.avg(JobApplication.fit_score_pct).label("avg_fit"),
            func.max(JobApplication.fit_score_pct).label("max_fit"),
            func.min(JobApplication.fit_score_pct).label("min_fit"),
            func.count(JobApplication.fit_score_pct).label("analyzed"),
        ).where(user_filter, JobApplication.fit_score.is_not(None))
    )
    fit_row = fit_agg.one()

    analyzed_count: int = fit_row.analyzed or 0
    pending_count: int = total_applications - analyzed_count
    avg_fit = round(float(fit_row.avg_fit), 1) if fit_row.avg_fit is not None else None
    highest_fit = int(fit_row.max_fit) if fit_row.max_fit is not None else None
    lowest_fit = int(fit_row.min_fit) if fit_row.min_fit is not None else None

    # ------------------------------------------------------------------
    # Query 3 - Weekly application counts (last 8 weeks)
    # ------------------------------------------------------------------
    cutoff = datetime.now(timezone.utc) - timedelta(days=56)
    weekly_rows = await db.execute(
        select(JobApplication.created_at)
        .where(user_filter, JobApplication.created_at >= cutoff)
    )
    created_dates = [row.created_at for row in weekly_rows]

    # Build complete 8-week skeleton (oldest to newest)
    now = datetime.now(timezone.utc)
    week_keys: list[str] = []
    for weeks_ago in range(7, -1, -1):
        week_start = now - timedelta(weeks=weeks_ago)
        week_keys.append(week_start.strftime("%Y-W%W"))

    week_counter: Counter = Counter()
    for dt in created_dates:
        week_counter[dt.strftime("%Y-W%W")] += 1

    weekly_applications = [
        WeeklyCount(week=wk, count=week_counter.get(wk, 0))
        for wk in week_keys
    ]

    # ------------------------------------------------------------------
    # Query 4 - Top 10 missing skills
    # ------------------------------------------------------------------
    skill_rows = await db.execute(
        select(JobApplication.missing_skills)
        .where(user_filter, JobApplication.missing_skills.is_not(None))
    )
    skill_counter: Counter = Counter()
    for row in skill_rows:
        skills = row.missing_skills
        if isinstance(skills, list):
            for skill in skills:
                if skill:
                    skill_counter[skill] += 1

    top_missing_skills = [
        SkillGap(skill=skill, count=count)
        for skill, count in skill_counter.most_common(10)
    ]

    # ------------------------------------------------------------------
    # Query 5 - Conversion rates
    # ------------------------------------------------------------------
    interview_count = status_counts.get("interview", 0)
    offer_count = status_counts.get("offer", 0)

    if total_applications > 0:
        interview_rate = round((interview_count + offer_count) / total_applications * 100, 1)
        offer_rate = round(offer_count / total_applications * 100, 1)
    else:
        interview_rate = 0.0
        offer_rate = 0.0

    return AnalyticsSummaryResponse(
        total_applications=total_applications,
        by_status=by_status,
        avg_fit_score_pct=avg_fit,
        highest_fit_score_pct=highest_fit,
        lowest_fit_score_pct=lowest_fit,
        analyzed_count=analyzed_count,
        pending_count=pending_count,
        weekly_applications=weekly_applications,
        top_missing_skills=top_missing_skills,
        interview_rate=interview_rate,
        offer_rate=offer_rate,
    )
