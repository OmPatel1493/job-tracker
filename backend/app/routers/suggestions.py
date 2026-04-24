"""
Suggestions router.

  POST /suggestions/{application_id}/generate - generate (or regenerate) AI resume suggestions
  GET  /suggestions/{application_id}          - fetch stored suggestions for an application

WHY upsert (update-or-create) on generate:
    Re-generating should refresh the suggestions in place rather than
    accumulating duplicate rows. One suggestion record per application
    keeps the schema simple and queries fast.

WHY 400 when resume or analysis is missing:
    generate_resume_suggestions() needs resume text and missing_skills.
    Returning a clear 400 with an actionable message is better than
    letting the AI call fail silently or return empty results.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.ai_suggestion import AiSuggestion
from app.models.job_application import JobApplication
from app.models.resume import Resume
from app.models.user import User
from app.schemas.suggestion import SuggestionResponse
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


async def _get_application(
    application_id: int,
    current_user: User,
    db: AsyncSession,
) -> JobApplication:
    """Fetch application and verify ownership. Raises 404 if not found."""
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return application


def _build_response(record: AiSuggestion) -> SuggestionResponse:
    """Parse suggestion_text JSON and return a SuggestionResponse."""
    suggestions = json.loads(record.suggestion_text)
    return SuggestionResponse(
        id=record.id,
        application_id=record.application_id,
        suggestions=suggestions,
        generated_at=record.generated_at,
    )


@router.post("/{application_id}/generate", response_model=SuggestionResponse)
async def generate_suggestions(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI resume suggestions for an application and store them.

    Requires the user to have an uploaded resume and a completed AI analysis
    (fit_score is not None). On success, upserts the suggestions row so
    re-generating always reflects the latest resume and analysis.
    """
    application = await _get_application(application_id, current_user, db)

    # Verify resume exists
    resume_result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
    resume = resume_result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a resume first.",
        )

    # Verify analysis has completed
    if application.fit_score is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wait for AI analysis to complete first.",
        )

    suggestions = ai_service.generate_resume_suggestions(
        resume_text=resume.raw_text,
        jd_text=application.job_description,
        missing_skills=application.missing_skills or [],
        job_title=application.job_title,
        company_name=application.company_name,
    )

    suggestion_text = json.dumps(suggestions)

    # Upsert: update existing record or create new one
    existing_result = await db.execute(
        select(AiSuggestion).where(AiSuggestion.application_id == application_id)
    )
    record = existing_result.scalar_one_or_none()

    if record is not None:
        from datetime import datetime, timezone
        record.suggestion_text = suggestion_text
        record.generated_at = datetime.now(timezone.utc)
    else:
        record = AiSuggestion(
            application_id=application_id,
            suggestion_text=suggestion_text,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)

    logger.info("Suggestions generated for application %s (user %s).", application_id, current_user.id)
    return _build_response(record)


@router.get("/{application_id}", response_model=SuggestionResponse)
async def get_suggestions(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return stored suggestions for an application.

    Returns 404 if no suggestions have been generated yet, with a message
    directing the user to POST /generate first.
    """
    await _get_application(application_id, current_user, db)

    result = await db.execute(
        select(AiSuggestion).where(AiSuggestion.application_id == application_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No suggestions yet. POST to /suggestions/{application_id}/generate first.",
        )

    return _build_response(record)
