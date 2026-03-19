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
"""

import json

import google.generativeai as genai

from app.config import settings

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
# Public function
# ---------------------------------------------------------------------------

async def extract_skills(resume_text: str) -> dict[str, list[str]]:
    """
    Send resume_text to gemini-1.5-flash and return a dict of categorised skills.

    Returns a dict like:
      {
        "technical_skills": [...],
        "tools_and_platforms": [...],
        ...
      }

    Raises:
      ValueError — if GEMINI_API_KEY is not configured.
      google.api_core.exceptions.GoogleAPIError — on API failures (propagated to caller).
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file to use AI features."
        )

    model = _get_model()
    prompt = _PROMPT_TEMPLATE.format(resume_text=resume_text)

    response = await model.generate_content_async(prompt)
    raw = response.text or "{}"
    return json.loads(raw)
