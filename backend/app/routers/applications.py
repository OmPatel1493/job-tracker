"""
Applications router — Day 19: POST create + POST reanalyze only.

WHY only POST today:
    GET / PATCH / DELETE come on Day 20 once we confirm the create
    flow (background pipeline, new schema) works end-to-end first.

WHY BackgroundTasks for the pipeline:
    AI analysis (Gemini + Pinecone) can take 2-5 s. Blocking the HTTP
    response on that would feel slow and risks timeout errors. Instead
    we commit the application row, return 201 immediately, and let the
    pipeline enrich it in the background. The AI fields start as None
    and are filled in once the background task completes.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.job_application import JobApplication
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationResponse
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
