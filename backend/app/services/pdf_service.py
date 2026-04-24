"""
PDF text extraction service.

WHY pdfplumber:
- Built on pdfminer.six - accurate character-level text positioning
- Handles multi-column layouts and tables better than PyPDF2/pypdf
- Returns plain text per page, easy to join and clean
- No external binaries required (unlike pdftotext)
"""

import io
import re

import pdfplumber

from app.utils.exceptions import PDFParseError, ResumeValidationError

# pdfminer is a pdfplumber dependency - import its password error directly
try:
    from pdfminer.pdfdocument import PDFPasswordIncorrect
except ImportError:  # pragma: no cover
    PDFPasswordIncorrect = Exception  # type: ignore[misc,assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_EXTRACTED_CHARS = 100_000  # ~20,000 words - more than any real resume


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """
    Normalise extracted text:
    - Remove null bytes / non-UTF8-safe control characters
    - Collapse more than 2 consecutive spaces to 2
    - Strip leading/trailing whitespace from each line
    - Collapse more than 2 consecutive newlines to 2
    """
    text = text.replace("\x00", "")
    text = re.sub(r" {3,}", "  ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF supplied as raw bytes.

    Cleans the extracted text (whitespace, null bytes, newlines) before
    returning so callers always receive normalised output.

    Raises:
        PDFParseError: if the PDF is password-protected, corrupted, or
                       contains no extractable text (e.g. scanned image).
        ResumeValidationError: if extracted text exceeds MAX_EXTRACTED_CHARS.

    WHY bytes not file path: FastAPI uploads arrive as bytes in memory;
    avoiding a temp-file write keeps the service stateless.

    WHY catch PDFPasswordIncorrect separately:
        Password-protected PDFs open without error but yield no text pages
        in some pdfminer versions; in others they raise PDFPasswordIncorrect
        immediately. Catching explicitly lets us give a clear user message.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())

    except PDFPasswordIncorrect:
        raise PDFParseError(
            "PDF is password-protected.",
            detail="Remove the password before uploading.",
        )
    except Exception as exc:
        raise PDFParseError(
            "PDF could not be parsed.",
            detail=f"The file may be corrupted or in an unsupported format. ({exc})",
        )

    if not pages_text:
        raise PDFParseError(
            "PDF contains no extractable text.",
            detail=(
                "This is likely a scanned image PDF. "
                "Please upload a text-based PDF or paste the resume text directly."
            ),
        )

    raw = "\n\n".join(pages_text)
    cleaned = _clean_text(raw)

    if len(cleaned) > MAX_EXTRACTED_CHARS:
        raise ResumeValidationError(
            f"Extracted text exceeds the {MAX_EXTRACTED_CHARS:,}-character limit.",
            detail="Please upload a shorter resume (max ~20,000 words).",
        )

    return cleaned


# Backward-compatible alias used by resume.py router
extract_text_from_bytes = extract_text_from_pdf


def extract_text_from_plain(text: str) -> str:
    """
    Accept raw plain text and apply the same cleaning rules as
    extract_text_from_pdf.

    WHY this exists: users may paste resume text directly instead of
    uploading a PDF. The cleaning pipeline should be identical so
    downstream AI services receive consistently formatted input.
    """
    return _clean_text(text)


def validate_resume_text(text: str) -> tuple[bool, str]:
    """
    Validate that extracted resume text is usable for AI processing.

    Returns:
        (False, reason)  if the text is too short to be a real resume.
        (True,  "OK")    if the text passes all checks.

    WHY validate length: a 50-character string cannot contain meaningful
    resume content - catching this early avoids a wasted API call.
    """
    if len(text) < 100:
        return False, "Resume text too short to be valid"
    if len(text) < 300:
        return False, "Resume text suspiciously short"
    return True, "OK"


def get_word_count(text: str) -> int:
    """
    Return the word count of the given text.

    WHY useful: a quick sanity check before sending text to an AI model -
    e.g. flag a resume with fewer than 50 words as likely incomplete.
    """
    return len(text.split())

