"""
AI service — all direct Gemini API calls for the application live here.

WHY a dedicated ai_service.py:
  skill_extractor.py handles resume text. ai_service.py handles job description
  text and any other AI tasks. Keeping them separate means each file has one
  responsibility and stays easy to read and test.

WHY Gemini gemini-1.5-flash:
  Free tier, fast, accurate at structured JSON extraction tasks.
  No credit card required — get a key at https://aistudio.google.com/apikey
"""

import json
import logging

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level setup
# ---------------------------------------------------------------------------

genai.configure(api_key=settings.GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"
MAX_JD_LENGTH = 15_000  # chars — more than any real job description needs


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def extract_jd_skills(jd_text: str) -> dict:
    """
    Extract structured skills from a job description using Gemini.

    Truncates input to MAX_JD_LENGTH chars before sending.
    Returns a dict with 'required' and 'preferred' skill categories,
    plus experience_years, job_level, and domain fields.

    Falls back to _fallback_jd_extraction() if the API call fails or
    returns unparseable JSON.

    WHY separate required/preferred:
        Job descriptions distinguish between must-have and nice-to-have skills.
        Surfacing this lets the UI show the user which gaps are critical vs optional.

    WHY strip markdown fences:
        Even with explicit instructions, language models occasionally wrap JSON
        in ```json ... ``` blocks. Stripping them before json.loads() prevents a
        parse error on an otherwise valid response.
    """
    text = jd_text[:MAX_JD_LENGTH]

    prompt = (
        "You are an expert technical recruiter and job description analyzer.\n"
        "Analyze this job description and extract all skills.\n"
        "Return ONLY this JSON structure with no markdown, no explanation,\n"
        "no code blocks — raw JSON only:\n"
        "{\n"
        '  "required": {\n'
        '    "languages": [],\n'
        '    "frameworks": [],\n'
        '    "tools": [],\n'
        '    "concepts": [],\n'
        '    "other": []\n'
        "  },\n"
        '  "preferred": {\n'
        '    "languages": [],\n'
        '    "frameworks": [],\n'
        '    "tools": [],\n'
        '    "concepts": [],\n'
        '    "other": []\n'
        "  },\n"
        '  "experience_years": null,\n'
        '  "job_level": "",\n'
        '  "domain": ""\n'
        "}\n"
        "experience_years: integer if mentioned, else null\n"
        "job_level: one of junior/mid/senior/lead/any\n"
        "domain: backend/frontend/data science/devops/fullstack/ml engineer/etc\n\n"
        f"Job Description:\n{text}"
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        raw = response.text or ""

        # Strip accidental markdown fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw.strip())

    except json.JSONDecodeError:
        logger.warning("Gemini returned malformed JSON for JD extraction — using fallback.")
        return _fallback_jd_extraction(jd_text)

    except Exception as exc:
        logger.warning("Gemini JD extraction failed (%s) — using fallback.", exc)
        return _fallback_jd_extraction(jd_text)


def flatten_jd_skills(jd_skills: dict) -> list[str]:
    """
    Flatten the required + preferred sections of a jd_skills dict into a
    single deduplicated list of skill strings.

    Normalises each skill to title case so 'python' and 'Python' are treated
    as the same entry.

    WHY flatten:
        compare_skills() in skill_extractor.py works on flat lists.
        Flattening here keeps the comparison logic simple.
    """
    seen: set[str] = set()
    flat: list[str] = []

    for section in ("required", "preferred"):
        section_data = jd_skills.get(section, {})
        if not isinstance(section_data, dict):
            continue
        for skills in section_data.values():
            if not isinstance(skills, list):
                continue
            for skill in skills:
                key = skill.lower()
                if key not in seen:
                    seen.add(key)
                    flat.append(skill.title())

    return flat


def extract_job_metadata(jd_text: str) -> dict:
    """
    Extract company name, job title, location, remote status, and salary
    range from a job description using Gemini.

    Returns a dict with keys:
        company_name, job_title, location, remote, salary_range

    Returns {} on any failure — metadata extraction is best-effort and
    should never block the main skill-matching flow.

    WHY best-effort (return {} on failure):
        Metadata is a convenience feature. If Gemini is unavailable or the
        JD doesn't mention a salary, the user can still get skill matching.
        Crashing here would degrade the whole feature for a minor enrichment.
    """
    text = jd_text[:MAX_JD_LENGTH]

    prompt = (
        "Extract from this job description and return raw JSON only\n"
        "(no markdown, no explanation):\n"
        "{\n"
        '  "company_name": "",\n'
        '  "job_title": "",\n'
        '  "location": "",\n'
        '  "remote": null,\n'
        '  "salary_range": ""\n'
        "}\n"
        "Use null for any field not found.\n\n"
        f"Job Description:\n{text}"
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        raw = response.text or ""

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw.strip())

    except Exception as exc:
        logger.warning("extract_job_metadata failed (%s) — returning empty dict.", exc)
        return {}


# ---------------------------------------------------------------------------
# Private fallback
# ---------------------------------------------------------------------------

def _fallback_jd_extraction(jd_text: str) -> dict:
    """
    Regex-based fallback for extract_jd_skills — no API call.

    Uses skill_extractor.extract_skills_with_regex() to scan the JD text
    against the known SKILL_CATEGORIES list. Returns the same dict structure
    as extract_jd_skills() so callers need no special-case handling.

    WHY same skills for required and preferred:
        Without AI we cannot distinguish required from preferred. Duplicating
        the matches into both sections is conservative — the user sees all
        matched skills rather than none.
    """
    from app.services.skill_extractor import extract_skills_with_regex

    skills = extract_skills_with_regex(jd_text)

    return {
        "required": skills,
        "preferred": skills,
        "experience_years": None,
        "job_level": "any",
        "domain": "unknown",
    }


# ---------------------------------------------------------------------------
# Inline tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    SAMPLE_JD = (
        "We are looking for a Senior Backend Engineer to join our team. "
        "You will design and build scalable REST APIs using Python and FastAPI. "
        "Requirements: 5+ years of experience, strong knowledge of Python, "
        "PostgreSQL, Docker, and AWS. Experience with Redis and Kubernetes is "
        "a plus. You should be comfortable with CI/CD pipelines and Agile "
        "methodologies. Preferred: experience with Machine Learning pipelines "
        "and familiarity with React for occasional frontend work. "
        "We offer a competitive salary range of $130,000 - $160,000. "
        "This is a remote-friendly position based in New York. "
        "The role involves system design, code reviews, and mentoring junior "
        "engineers. You will work with a team of 8 engineers on a SaaS platform "
        "serving over 500,000 users. Apply if you are passionate about clean "
        "code, distributed systems, and building reliable infrastructure."
    )

    # Test fallback (no API key needed)
    result = _fallback_jd_extraction(SAMPLE_JD)
    assert "required" in result, "fallback should return required key"
    assert result["job_level"] == "any"
    assert result["domain"] == "unknown"
    print(f"PASS: _fallback_jd_extraction — {result}")

    # Test flatten_jd_skills
    flat = flatten_jd_skills(result)
    assert isinstance(flat, list), "should return a list"
    assert len(flat) == len({s.lower() for s in flat}), "no duplicates"
    print(f"PASS: flatten_jd_skills — {flat}")

    # Test extract_job_metadata fallback path (no key = returns {} or partial)
    meta = extract_job_metadata(SAMPLE_JD)
    assert isinstance(meta, dict), "should always return a dict"
    print(f"PASS: extract_job_metadata returned dict — {meta}")
