"""
Custom exception classes for the resume pipeline.

WHY custom exceptions (not plain ValueError/RuntimeError):
  Using specific exception types lets each layer catch exactly what it
  understands and re-raise everything else. A router can catch
  PDFParseError and return 422 without accidentally swallowing an
  unrelated RuntimeError from a different subsystem.
"""


class PDFParseError(ValueError):
    """
    Raised when a PDF cannot be parsed.

    Covers: corrupted files, password-protected PDFs, image-only PDFs,
    and any other pdfplumber/pdfminer failure.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail or message


class SkillExtractionError(RuntimeError):
    """
    Raised when skill extraction fails unrecoverably.

    In practice this is only raised when both the AI call AND the regex
    fallback fail - which should never happen unless the input is empty.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail or message


class VectorServiceError(RuntimeError):
    """
    Raised when a Pinecone or embedding operation fails.

    Distinct from RuntimeError so routers can return 503 (service
    unavailable) rather than 500 (internal server error).
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail or message


class ResumeValidationError(ValueError):
    """
    Raised when extracted resume text fails content validation.

    Examples: text too short, character limit exceeded, empty after cleaning.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail or message
