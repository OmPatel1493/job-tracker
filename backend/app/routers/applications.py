"""
Applications router — Day 19/20: POST create/reanalyze + GET list/detail/stats.

WHY BackgroundTasks for the pipeline:
    AI analysis (Gemini + Pinecone) can take 2-5 s. Blocking the HTTP
    response on that would feel slow and risks timeout errors. Instead
    we commit the application row, return 201 immediately, and let the
    pipeline enrich it in the background. The AI fields start as None
    and are filled in once the background task completes.

WHY /stats/summary is defined before /{application_id}:
    FastAPI matches routes in declaration order. If /{application_id}
    came first, the literal path segment "stats" would be parsed as an
    int, causing a 422 validation error. Fixed by declaring the static
    path first.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.job_application import JobApplication
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatsResponse,
)
from app.services import pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


# ---------------------------------------------------------------------------
# POST /applications/  — create
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a new job application and trigger AI matching in the background.

    Step 1 — persist the row immediately.  All AI fields (fit_score,
    matched_skills, etc.) are left as None until the pipeline fills them in.

    Step 2 — enqueue the AI pipeline as a BackgroundTask so the caller
    gets an instant HTTP 201 without waiting for Gemini / Pinecone.

    Returns ApplicationResponse fields plus a 'message' key confirming
    that analysis has been queued.
    """
    application = JobApplication(
        user_id=current_user.id,
        company_name=body.company_name,
        job_title=body.job_title,
        job_description=body.job_description,
        notes=body.notes,
        applied_date=body.applied_date,
        job_url=body.job_url,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    background_tasks.add_task(
        pipeline_service.run_application_pipeline,
        db,
        application.id,
        current_user.id,
    )

    logger.info(
        "Application %s created for user %s — AI pipeline queued.",
        application.id,
        current_user.id,
    )

    data = ApplicationResponse.model_validate(application).model_dump()
    data["message"] = "Application saved. AI analysis running in background."
    return data


# ---------------------------------------------------------------------------
# POST /applications/{id}/reanalyze  — re-run pipeline
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/reanalyze",
    status_code=status.HTTP_202_ACCEPTED,
)
async def reanalyze_application(
    application_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-trigger the AI matching pipeline for an existing application.

    Useful after the user uploads a new resume and wants refreshed fit
    scores without creating a duplicate application row.

    Returns 404 if the application does not exist or belongs to a
    different user.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    background_tasks.add_task(
        pipeline_service.rerun_pipeline,
        db,
        application_id,
        current_user.id,
    )

    logger.info(
        "Reanalysis queued for application %s (user %s).",
        application_id,
        current_user.id,
    )
    return {"message": "Reanalysis started", "application_id": application_id}


# ---------------------------------------------------------------------------
# GET /applications/stats/summary  — aggregate stats
# NOTE: must be declared BEFORE /{application_id} (see module docstring)
# ---------------------------------------------------------------------------

@router.get(
    "/stats/summary",
    response_model=ApplicationStatsResponse,
)
async def get_stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return aggregate statistics for the current user's applications.

    All aggregation is done in a single DB round-trip per query using
    SQLAlchemy func — no Python loops over result sets.
    """
    user_filter = JobApplication.user_id == current_user.id

    # Total count
    total: int = await db.scalar(
        select(func.count()).select_from(JobApplication).where(user_filter)
    ) or 0

    # Count per status
    status_rows = await db.execute(
        select(JobApplication.status, func.count().label("n"))
        .where(user_filter)
        .group_by(JobApplication.status)
    )
    by_status: dict[str, int] = {row.status: row.n for row in status_rows}

    # Fit-score aggregates (only over rows that have been analyzed)
    agg_row = await db.execute(
        select(
            func.avg(JobApplication.fit_score).label("avg_fit"),
            func.max(JobApplication.fit_score).label("max_fit"),
            func.count(JobApplication.fit_score).label("analyzed"),
        ).where(user_filter)
    )
    agg = agg_row.one()

    analyzed_count: int = agg.analyzed or 0
    pending_count: int = total - analyzed_count
    avg_fit = round(float(agg.avg_fit), 4) if agg.avg_fit is not None else None
    highest_fit = round(float(agg.max_fit), 4) if agg.max_fit is not None else None

    return ApplicationStatsResponse(
        total=total,
        by_status=by_status,
        avg_fit_score=avg_fit,
        highest_fit_score=highest_fit,
        analyzed_count=analyzed_count,
        pending_analysis_count=pending_count,
    )


# ---------------------------------------------------------------------------
# GET /applications/  — paginated list
# ---------------------------------------------------------------------------

@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    response: Response,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|fit_score_pct)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a paginated, filterable list of the user's applications.

    Query params:
        status      — filter by exact status value
        search      — case-insensitive substring match on company_name or job_title
        sort_by     — "created_at" (default) or "fit_score_pct"
        order       — "desc" (default) or "asc"
        limit       — page size, 1–100 (default 20)
        offset      — number of rows to skip (default 0)

    Sets X-Total-Count response header to the unfiltered+filtered row count
    so the frontend can build pagination controls without a second request.
    """
    base_filter = JobApplication.user_id == current_user.id

    filters = [base_filter]
    if status_filter:
        filters.append(JobApplication.status == status_filter)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                JobApplication.company_name.ilike(term),
                JobApplication.job_title.ilike(term),
            )
        )

    # Total matching rows (for X-Total-Count header)
    total: int = await db.scalar(
        select(func.count()).select_from(JobApplication).where(*filters)
    ) or 0

    # Sort column + direction
    sort_col = (
        JobApplication.fit_score_pct
        if sort_by == "fit_score_pct"
        else JobApplication.created_at
    )
    order_fn = asc if order == "asc" else desc

    rows = await db.execute(
        select(JobApplication)
        .where(*filters)
        .order_by(order_fn(sort_col))
        .limit(limit)
        .offset(offset)
    )
    items = rows.scalars().all()

    response.headers["X-Total-Count"] = str(total)

    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(app) for app in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /applications/{id}  — single detail
# ---------------------------------------------------------------------------

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return full detail for a single application, including all AI fields.

    Sets 'analysis_status' to "pending" when the pipeline hasn't run yet
    (fit_score is None) and "complete" once it has.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    data = ApplicationDetailResponse.model_validate(application).model_dump()
    data["analysis_status"] = "pending" if application.fit_score is None else "complete"
    return data
