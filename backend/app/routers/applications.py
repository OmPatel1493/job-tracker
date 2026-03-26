"""
Applications router.

<<<<<<< Updated upstream
  POST   /applications                 — create + fire AI pipeline (BackgroundTask)
  POST   /applications/{id}/reanalyze  — re-run pipeline for existing application
  GET    /applications/stats/summary   — aggregate stats
  GET    /applications                 — paginated list (filter / search / sort)
  GET    /applications/{id}            — full detail + analysis_status
  PATCH  /applications/{id}/status     — update status (+ optional notes)
  PATCH  /applications/{id}/notes      — update notes only
  DELETE /applications/{id}            — delete application
=======
  POST   /applications                 - create + fire AI pipeline (BackgroundTask)
  POST   /applications/{id}/reanalyze  - re-run pipeline for existing application
  GET    /applications/stats/summary   - aggregate stats
  GET    /applications                 - paginated list (filter / search / sort)
  GET    /applications/{id}            - full detail + analysis_status
  PATCH  /applications/{id}/status     - update status (+ optional notes)
  PATCH  /applications/{id}/notes      - update notes only
  DELETE /applications/{id}            - delete application
>>>>>>> Stashed changes

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
from datetime import datetime, timezone
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
    ApplicationNotesUpdate,
    ApplicationResponse,
    ApplicationStatsResponse,
    ApplicationStatusUpdate,
)
from app.services import pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a new job application and trigger AI matching in the background.

    Persists the row immediately with AI fields as None, then enqueues
    the pipeline as a BackgroundTask so the caller gets an instant 201
    without waiting for Gemini / Pinecone.
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
        "Application %s created for user %s - AI pipeline queued.",
        application.id,
        current_user.id,
    )

    data = ApplicationResponse.model_validate(application).model_dump()
    data["message"] = "Application saved. AI analysis running in background."
    return data


@router.post("/{application_id}/reanalyze", status_code=status.HTTP_202_ACCEPTED)
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
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    background_tasks.add_task(
        pipeline_service.rerun_pipeline,
        db,
        application_id,
        current_user.id,
    )

    logger.info("Reanalysis queued for application %s (user %s).", application_id, current_user.id)
    return {"message": "Reanalysis started", "application_id": application_id}


@router.get("/stats/summary", response_model=ApplicationStatsResponse)
async def get_stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return aggregate statistics for the current user's applications.

<<<<<<< Updated upstream
    All aggregation is done via SQLAlchemy func — no Python loops.
=======
    All aggregation is done via SQLAlchemy func - no Python loops.
>>>>>>> Stashed changes
    """
    user_filter = JobApplication.user_id == current_user.id

    total: int = await db.scalar(
        select(func.count()).select_from(JobApplication).where(user_filter)
    ) or 0

    status_rows = await db.execute(
        select(JobApplication.status, func.count().label("n"))
        .where(user_filter)
        .group_by(JobApplication.status)
    )
    by_status: dict[str, int] = {row.status: row.n for row in status_rows}

    agg_row = await db.execute(
        select(
            func.avg(JobApplication.fit_score).label("avg_fit"),
            func.max(JobApplication.fit_score).label("max_fit"),
            func.count(JobApplication.fit_score).label("analyzed"),
        ).where(user_filter)
    )
    agg = agg_row.one()

    analyzed_count: int = agg.analyzed or 0
    avg_fit = round(float(agg.avg_fit), 4) if agg.avg_fit is not None else None
    highest_fit = round(float(agg.max_fit), 4) if agg.max_fit is not None else None

    return ApplicationStatsResponse(
        total=total,
        by_status=by_status,
        avg_fit_score=avg_fit,
        highest_fit_score=highest_fit,
        analyzed_count=analyzed_count,
        pending_analysis_count=total - analyzed_count,
    )


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

    Sets X-Total-Count response header for pagination controls.
    """
    filters = [JobApplication.user_id == current_user.id]
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

    total: int = await db.scalar(
        select(func.count()).select_from(JobApplication).where(*filters)
    ) or 0

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


@router.get("/{application_id}", response_model=ApplicationDetailResponse)
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return full detail for a single application including all AI fields.

    Sets analysis_status to "pending" when fit_score is None, "complete" otherwise.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    data = ApplicationDetailResponse.model_validate(application).model_dump()
    data["analysis_status"] = "pending" if application.fit_score is None else "complete"
    return data


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    body: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of an application, and optionally its notes.

    WHY a dedicated /status endpoint (not a generic PATCH):
        Keeping status updates explicit prevents accidental overwrites of
        AI fields. A generic PATCH with exclude_unset could still clobber
        fields if the client sends unexpected keys.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    application.status = body.status
    if body.notes is not None:
        application.notes = body.notes
    application.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)
    return ApplicationResponse.model_validate(application)


@router.patch("/{application_id}/notes", response_model=ApplicationResponse)
async def update_application_notes(
    application_id: int,
    body: ApplicationNotesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Replace the free-text notes on an application.

    Separate from /status so the frontend can autosave notes without
    accidentally touching the status field.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    application.notes = body.notes
    application.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)
    return ApplicationResponse.model_validate(application)


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete an application row.

    WHY return a body (not 204 No Content):
        A JSON confirmation with the deleted ID lets the frontend update
        local state by ID without needing to parse a 204 response.
    """
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    await db.delete(application)
    await db.commit()

    logger.info("Application %s deleted by user %s.", application_id, current_user.id)
    return {"message": "Application deleted", "deleted_id": str(application_id)}
