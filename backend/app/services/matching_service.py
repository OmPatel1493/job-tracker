"""
Matching service - orchestrates semantic similarity and skill overlap scoring
to produce a single "fit score" for a resume vs. job description.

WHY a dedicated matching_service.py:
  vector_service.py handles Pinecone/embeddings.
  skill_extractor.py handles resume skill parsing.
  ai_service.py handles JD skill parsing.
  This module combines their outputs into one final score so the router
  only needs to call run_full_matching() and get back a ready-to-return dict.

WHY two scoring signals (semantic + skill overlap):
  - Semantic score (Pinecone cosine): captures overall meaning similarity -
    "experienced Python engineer" and "Python developer" score high even
    though the words differ.
  - Skill overlap score: counts exact skill matches - a precise signal for
    hard requirements like "must know Kubernetes".
  Combining both (60/40 weighted) is more reliable than either alone.
"""

import logging

from app.services import ai_service, skill_extractor, vector_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------------

def compute_semantic_score(jd_text: str, user_id: str) -> float:
    """
    Return the cosine similarity between the user's stored resume embedding
    and the given job description text.

    Calls vector_service.query_similar_to_jd() and returns its score.
    Returns 0.0 if no resume has been stored for this user yet, or if
    the vector service is unavailable.

    Args:
        jd_text:  Plain text of the job description.
        user_id:  The authenticated user's ID (used to filter Pinecone).

    Returns:
        Float in range [0.0, 1.0], rounded to 4 decimal places.

    WHY round to 4 places:
        Pinecone returns scores with many decimal places. 4 places is precise
        enough for display and comparison while keeping the value clean.
    """
    try:
        score = vector_service.query_similar_to_jd(jd_text, user_id)
    except Exception as exc:
        logger.warning("compute_semantic_score failed (%s) - defaulting to 0.0.", exc)
        score = 0.0

    return round(float(score), 4)


def compute_skill_overlap_score(
    resume_skills: list[str],
    jd_skills: list[str],
) -> float:
    """
    Calculate what fraction of the JD's required skills appear in the resume.

    Comparison is case-insensitive so "python" and "Python" are treated as
    the same skill.

    Args:
        resume_skills: Flat list of skills extracted from the resume.
        jd_skills:     Flat list of skills required by the job description.

    Returns:
        Float in range [0.0, 1.0], rounded to 4 decimal places.
        Returns 0.0 if jd_skills is empty (no skills to match against).

    WHY jd_skills as denominator (not resume_skills):
        We want to know how well the resume covers the job requirements,
        not how many of the resume's skills appear in the JD. A resume with
        100 skills always covering 10 JD skills is a 100% match by resume
        denominator - misleading. JD denominator is the correct signal.
    """
    if not jd_skills:
        return 0.0

    resume_lower = {s.lower() for s in resume_skills}
    matched_count = sum(1 for s in jd_skills if s.lower() in resume_lower)
    score = matched_count / len(jd_skills)
    return round(score, 4)


def compute_fit_score(
    semantic_score: float,
    skill_overlap_score: float,
) -> float:
    """
    Combine semantic similarity and skill overlap into a single fit score.

    Formula: (semantic_score * 0.6) + (skill_overlap_score * 0.4)

    Args:
        semantic_score:       Cosine similarity from Pinecone (0.0–1.0).
        skill_overlap_score:  Fraction of JD skills found in resume (0.0–1.0).

    Returns:
        Weighted combined score in range [0.0, 1.0], rounded to 4 decimal places.

    WHY 60/40 weighting:
        Semantic score captures holistic meaning - more robust to phrasing
        differences. Skill overlap is precise but brittle (misses synonyms).
        Weighting semantic higher rewards candidates who genuinely understand
        the domain even if their resume uses different terminology.
    """
    score = (semantic_score * 0.6) + (skill_overlap_score * 0.4)
    return round(score, 4)


def get_fit_label(fit_score: float) -> str:
    """
    Convert a numeric fit score into a human-readable label.

    Ranges:
        0.00 – 0.40 → "Poor Fit"
        0.41 – 0.60 → "Moderate Fit"
        0.61 – 0.75 → "Good Fit"
        0.76 – 0.90 → "Strong Fit"
        0.91 – 1.00 → "Excellent Fit"

    WHY string labels:
        Raw floats are not user-friendly. Labels give instant context -
        "Strong Fit" is immediately actionable; 0.8231 is not.
    """
    if fit_score <= 0.40:
        return "Poor Fit"
    if fit_score <= 0.60:
        return "Moderate Fit"
    if fit_score <= 0.75:
        return "Good Fit"
    if fit_score <= 0.90:
        return "Strong Fit"
    return "Excellent Fit"


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_full_matching(
    jd_text: str,
    jd_skills_dict: dict,
    resume_skills: list[str],
    user_id: str,
) -> dict:
    """
    Run the complete matching pipeline and return a structured result dict.

    Steps:
        1. Compute semantic score via Pinecone cosine similarity.
        2. Flatten the JD skills dict into a single list.
        3. Compute skill overlap score (resume vs JD skills).
        4. Compute weighted fit score.
        5. Compare skills to get matched and missing lists.
        6. Assemble and return the result dict.

    Args:
        jd_text:         Plain text of the job description (for embedding).
        jd_skills_dict:  Structured dict from ai_service.extract_jd_skills().
        resume_skills:   Flat list of skills from skill_extractor (resume).
        user_id:         Authenticated user ID for Pinecone filter.

    Returns:
        {
            "fit_score":           float,    # 0.0 to 1.0
            "fit_score_pct":       int,      # fit_score * 100
            "fit_label":           str,      # e.g. "Good Fit"
            "semantic_score":      float,
            "skill_overlap_score": float,
            "matched_skills":      list[str],
            "missing_skills":      list[str],
            "total_jd_skills":     int,
            "total_matched":       int,
            "total_missing":       int,
        }

    WHY one orchestrator function:
        The router only needs to call run_full_matching() with the data it
        already has. All the wiring between services stays here, not scattered
        across route handlers.
    """
    semantic_score = compute_semantic_score(jd_text, user_id)

    flat_jd_skills = ai_service.flatten_jd_skills(jd_skills_dict)

    skill_overlap_score = compute_skill_overlap_score(resume_skills, flat_jd_skills)

    fit_score = compute_fit_score(semantic_score, skill_overlap_score)

    matched_skills, missing_skills = skill_extractor.compare_skills(
        resume_skills, flat_jd_skills
    )

    return {
        "fit_score": fit_score,
        "fit_score_pct": int(fit_score * 100),
        "fit_label": get_fit_label(fit_score),
        "semantic_score": semantic_score,
        "skill_overlap_score": skill_overlap_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_jd_skills": len(flat_jd_skills),
        "total_matched": len(matched_skills),
        "total_missing": len(missing_skills),
    }


# ---------------------------------------------------------------------------
# Inline tests
# ---------------------------------------------------------------------------
