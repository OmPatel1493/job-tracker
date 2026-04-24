"""
Pipeline service - master orchestrator for the AI matching pipeline.

WHY a dedicated pipeline_service.py:
  The AI pipeline involves multiple stages across 4 different services. Putting
  this logic in a router would make it untestable and hard to follow. A dedicated
  orchestrator keeps each stage isolated, easy to log, and safe to re-run.

WHY run AFTER the application is saved:
  The application row must exist in the DB before we can update it with AI
  results. The router creates the row first, then fires the pipeline. This
  also means a pipeline failure never blocks the user from saving their
  application - the row always exists, AI fields just stay null until
  the pipeline completes.

WHY per-stage try/except:
  Each stage calls an external service (Gemini, Pinecone, MySQL). Any one of
  them can fail independently. Catching per-stage lets us log exactly which
  stage failed and return a useful error, rather than a generic 500.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_application import JobApplication
from app.models.resume import Resume
from app.services import ai_service, matching_service, skill_extractor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def run_application_pipeline(
    db: AsyncSession,
    application_id: int,
    user_id: int,
) -> dict:
    """
    Run the full AI matching pipeline for a saved application.

    Must be called AFTER the application row already exists in the DB.
    Enriches the application with JD skill extraction, semantic similarity,
    and skill gap analysis, then writes the results back to the DB.

    Args:
        db:              Async DB session (injected by FastAPI).
        application_id:  ID of the application to enrich.
        user_id:         ID of the authenticated user (for Pinecone filter).

    Returns:
        {"success": True, "result": {...}}  on success
        {"success": False, "error": "...", "failed_stage": "..."}  on failure
    """
    return await _run_pipeline(db, application_id, user_id, is_rerun=False)


async def rerun_pipeline(
    db: AsyncSession,
    application_id: int,
    user_id: int,
) -> dict:
    """
    Re-run the full AI matching pipeline for an existing application.

    Identical to run_application_pipeline but logs that it is a re-run.
    Used when the user uploads a new resume and wants to refresh their
    match scores without creating a new application.

    Args:
        db:              Async DB session (injected by FastAPI).
        application_id:  ID of the application to re-score.
        user_id:         ID of the authenticated user.

    Returns:
        Same shape as run_application_pipeline.
    """
    return await _run_pipeline(db, application_id, user_id, is_rerun=True)


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

async def _run_pipeline(
    db: AsyncSession,
    application_id: int,
    user_id: int,
    is_rerun: bool,
) -> dict:
    """
    Shared implementation for run_application_pipeline and rerun_pipeline.

    WHY one private function:
        Both public functions do exactly the same work. The only difference
        is the log message. Keeping one implementation avoids drift between
        the two code paths.
    """
    run_label = "re-run" if is_rerun else "run"
    logger.info(
        "Pipeline %s started - application_id=%s user_id=%s",
        run_label, application_id, user_id,
    )

    # Load application and resume from DB
    try:
        app_result = await db.execute(
            select(JobApplication).where(
                JobApplication.id == application_id,
                JobApplication.user_id == user_id,
            )
        )
        application = app_result.scalar_one_or_none()

        if application is None:
            logger.error("Pipeline load failed: application %s not found.", application_id)
            return {
                "success": False,
                "error": f"Application {application_id} not found.",
                "failed_stage": "load_data",
            }

        resume_result = await db.execute(
            select(Resume).where(Resume.user_id == user_id)
        )
        resume = resume_result.scalar_one_or_none()

        if resume is None:
            logger.warning(
                "Pipeline: no resume for user %s - writing note to application.",
                user_id,
            )
            application.notes = (
                (application.notes or "") +
                "\n[AI matching skipped: no resume uploaded yet.]"
            ).strip()
            await db.commit()
            return {"success": False, "error": "No resume found"}

    except Exception as exc:
        logger.exception("Pipeline load failed: %s", exc)
        return {"success": False, "error": str(exc), "failed_stage": "load_data"}

    # Extract JD skills via Gemini
    try:
        jd_skills_dict = ai_service.extract_jd_skills(application.job_description)
        logger.info("Pipeline: JD skills extracted.")
    except Exception as exc:
        logger.exception("Pipeline: JD skill extraction failed: %s", exc)
        return {"success": False, "error": str(exc), "failed_stage": "extract_jd_skills"}

    # Flatten skill lists
    try:
        flat_jd_skills = ai_service.flatten_jd_skills(jd_skills_dict)
        raw_resume_skills = resume.parsed_skills or {}
        flat_resume_skills = skill_extractor.flatten_skills(raw_resume_skills)
        logger.info(
            "Pipeline: %d JD skills, %d resume skills.",
            len(flat_jd_skills), len(flat_resume_skills),
        )
    except Exception as exc:
        logger.exception("Pipeline: flatten skills failed: %s", exc)
        return {"success": False, "error": str(exc), "failed_stage": "flatten_skills"}

    # Run full matching (semantic + skill overlap)
    try:
        matching_result = matching_service.run_full_matching(
            jd_text=application.job_description,
            jd_skills_dict=jd_skills_dict,
            resume_skills=flat_resume_skills,
            user_id=str(user_id),
        )
        logger.info(
            "Pipeline: fit_score=%.4f (%s).",
            matching_result["fit_score"],
            matching_result["fit_label"],
        )
    except Exception as exc:
        logger.exception("Pipeline: matching failed: %s", exc)
        return {"success": False, "error": str(exc), "failed_stage": "run_matching"}

    # Write results back to DB
    try:
        application.jd_skills = jd_skills_dict
        application.fit_score = matching_result["fit_score"]
        application.fit_score_pct = matching_result["fit_score_pct"]
        application.fit_label = matching_result["fit_label"]
        application.semantic_score = matching_result["semantic_score"]
        application.skill_overlap_score = matching_result["skill_overlap_score"]
        application.matched_skills = matching_result["matched_skills"]
        application.missing_skills = matching_result["missing_skills"]

        await db.commit()
        await db.refresh(application)
        logger.info("Pipeline: application %s updated in DB.", application_id)

    except Exception as exc:
        logger.exception("Pipeline: DB write failed: %s", exc)
        await db.rollback()
        return {"success": False, "error": str(exc), "failed_stage": "db_write"}

    logger.info("Pipeline %s complete - application_id=%s", run_label, application_id)
    return {"success": True, "result": matching_result}
