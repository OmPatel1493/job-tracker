"""
PDF text extraction service.

WHY pdfplumber:
- Built on pdfminer.six — accurate character-level text positioning
- Handles multi-column layouts and tables better than PyPDF2/pypdf
- Returns plain text per page, easy to join and clean
- No external binaries required (unlike pdftotext)
"""

import io

import pdfplumber


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extract all text from a PDF supplied as raw bytes.

    Returns the full text with pages separated by newlines.
    Raises ValueError if the PDF contains no extractable text
    (e.g. a scanned image-only PDF).

    WHY bytes not file path: FastAPI uploads arrive as bytes in memory;
    avoiding a temp-file write keeps the service stateless.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

    if not pages_text:
        raise ValueError(
            "No extractable text found. The PDF may be a scanned image. "
            "OCR support is not included yet."
        )

    return "\n\n".join(pages_text)


def extract_text_from_file(path: str) -> str:
    """
    Convenience wrapper for local file paths (useful in tests/scripts).
    Reads the file and delegates to extract_text_from_bytes.
    """
    with open(path, "rb") as f:
        return extract_text_from_bytes(f.read())
