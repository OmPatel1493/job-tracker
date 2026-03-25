from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.resume import (
    ResumeDeleteResponse,
    ResumeResponse,
    ResumeTextUpload,
    ResumeUploadResponse,
    SkillsDict,
    SkillsResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # Resume
    "SkillsDict",
    "ResumeTextUpload",
    "ResumeUploadResponse",
    "ResumeResponse",
    "SkillsResponse",
    "ResumeDeleteResponse",
]
