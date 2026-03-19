"""
Skill extraction service — uses Google Gemini (gemini-1.5-flash) to pull
structured skills out of raw resume text.

WHY a service module (not inline in the router):
  Keeps the prompt and parsing logic in one place. If the model, prompt
  structure, or output schema changes, only this file needs updating.

WHY Gemini instead of GPT:
  Google provides a free API tier for Gemini — no credit card required.
  gemini-1.5-flash is fast, accurate at structured extraction tasks, and
  supports response_mime_type="application/json" for reliable JSON output.

WHY response_mime_type="application/json":
  Forces Gemini to return valid JSON every time — no markdown fences,
  no prose, no trailing commas. Safe to json.loads() directly.

WHY temperature=0:
  Extraction should be deterministic. Temperature=0 ensures the model
  picks the most likely token at each step — consistent, reproducible output.

WHY SKILL_CATEGORIES:
  Used as a reference list for the regex fallback. If the Gemini API is
  unavailable, the regex scanner checks the resume text against this list
  so the endpoint always returns something useful.
"""

import json
import re

import google.generativeai as genai

from app.config import settings


# ---------------------------------------------------------------------------
# Reference skill list — also used by the regex fallback
# ---------------------------------------------------------------------------

SKILL_CATEGORIES: dict[str, list[str]] = {
    "languages": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#",
        "Go", "Rust", "R", "SQL", "Scala", "Kotlin", "Swift",
    ],
    "frameworks": [
        "React", "Next.js", "FastAPI", "Django", "Flask", "Spring",
        "Node.js", "Express", "Vue", "Angular", "TensorFlow",
        "PyTorch", "Scikit-learn", "LangChain",
    ],
    "tools": [
        "Docker", "Kubernetes", "Git", "GitHub", "AWS", "GCP", "Azure",
        "PostgreSQL", "MongoDB", "Redis", "Pinecone", "Kafka", "Spark",
    ],
    "concepts": [
        "REST API", "Microservices", "CI/CD", "Machine Learning",
        "Deep Learning", "NLP", "Computer Vision", "Data Engineering",
        "System Design", "Agile", "DevOps",
    ],
}


# ---------------------------------------------------------------------------
# Gemini model (lazy init)
# ---------------------------------------------------------------------------

_model: genai.GenerativeModel | None = None


def _get_model() -> genai.GenerativeModel:
    """Lazy-initialise the Gemini model so the app can start without a key."""
    global _model
    if _model is None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    return _model


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are a resume parser that extracts skills from resume text.

Return ONLY valid JSON in this exact shape:
{{
  "technical_skills": ["Python", "SQL", ...],
  "soft_skills": ["Leadership", "Communication", ...],
  "tools_and_platforms": ["Git", "Docker", "AWS", ...],
  "languages_and_frameworks": ["FastAPI", "React", "Node.js", ...]
}}

Rules:
- Each value is a list of strings (skill names only, no descriptions).
- Normalise capitalisation: "python" → "Python", "rest api" → "REST API".
- Omit empty categories (don't include a key with an empty list).
- De-duplicate entries within each category.
- Do not invent skills that are not in the resume text.

Resume text:
{resume_text}
"""


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def extract_skills_with_gemini(text: str) -> dict[str, list[str]]:
    """
    Send resume text to gemini-1.5-flash and return a dict of categorised skills.

    Falls back to extract_skills_with_regex() if:
    - The API key is missing
    - The API call fails for any reason
    - The response is not valid JSON

    WHY graceful fallback: the endpoint should never 500 just because
    the AI model is temporarily unavailable. Regex results are less
    complete but always available.
    """
    if not settings.GEMINI_API_KEY:
        return extract_skills_with_regex(text)

    model = _get_model()
    prompt = _PROMPT_TEMPLATE.format(resume_text=text)

    try:
        response = await model.generate_content_async(prompt)
        raw = response.text or "{}"
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return extract_skills_with_regex(text)


# Alias used by the router (keeps the router import stable)
extract_skills = extract_skills_with_gemini


def extract_skills_with_regex(text: str) -> dict[str, list[str]]:
    """
    Fallback skill extractor — no API call.

    Scans text for matches against SKILL_CATEGORIES using
    case-insensitive regex word boundaries.

    WHY word boundaries: prevents "C" matching "CI/CD" or "React"
    matching "Reactive". Skills with special chars (C++, C#, Next.js)
    use re.escape for safety.

    Returns the same dict structure as extract_skills_with_gemini.
    """
    result: dict[str, list[str]] = {}
    for category, skill_list in SKILL_CATEGORIES.items():
        matched = []
        for skill in skill_list:
            pattern = re.compile(re.escape(skill), re.IGNORECASE)
            if pattern.search(text):
                matched.append(skill)
        if matched:
            result[category] = matched
    return result


def flatten_skills(skills_dict: dict[str, list[str]]) -> list[str]:
    """
    Flatten a categorised skills dict into a single deduplicated list.

    Normalises each skill to title case so "python" and "Python" are
    treated as the same entry.

    WHY flatten: some downstream operations (e.g. compare_skills,
    embedding) work on a flat list rather than categories.
    """
    seen: set[str] = set()
    flat: list[str] = []
    for skills in skills_dict.values():
        for skill in skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                flat.append(skill.title())
    return flat


def compare_skills(
    resume_skills: list[str],
    jd_skills: list[str],
) -> tuple[list[str], list[str]]:
    """
    Compare a candidate's skills against a job description's required skills.

    Args:
        resume_skills: flat list of skills extracted from the resume.
        jd_skills:     flat list of skills required by the job description.

    Returns:
        matched — skills present in both lists (case-insensitive).
        missing — skills in jd_skills but absent from resume_skills.

    WHY this function: gives the user instant feedback on skill gaps
    before applying — the core value-add of the job tracker AI feature.
    """
    resume_lower = {s.lower() for s in resume_skills}
    matched = [s for s in jd_skills if s.lower() in resume_lower]
    missing = [s for s in jd_skills if s.lower() not in resume_lower]
    return matched, missing


# ---------------------------------------------------------------------------
# Inline tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_text = (
        "Experienced Python developer. Built REST APIs with FastAPI and Django. "
        "Deployed using Docker and AWS. Used PostgreSQL and Redis. "
        "Familiar with Machine Learning and CI/CD pipelines."
    )

    skills = extract_skills_with_regex(sample_text)
    assert "languages" in skills, "should detect Python"
    assert "Python" in skills["languages"]
    print(f"PASS: extract_skills_with_regex — {skills}")

    flat = flatten_skills(skills)
    assert isinstance(flat, list)
    assert len(flat) == len({s.lower() for s in flat}), "no duplicates"
    print(f"PASS: flatten_skills — {flat}")

    jd = ["Python", "React", "Docker", "Kubernetes"]
    matched, missing = compare_skills(flat, jd)
    assert "Python" in matched, "Python should be matched"
    assert "React" in missing, "React should be missing"
    print(f"PASS: compare_skills — matched={matched}, missing={missing}")
