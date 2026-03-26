import enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.note import Note
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"  # kept for backwards compatibility with existing data


class JobApplication(TimestampMixin, Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core job info
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status tracking
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    applied_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    # Free-text notes (inline, not a separate table)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI matching results (null until matching has been run)
    jd_skills: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fit_score_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    note_entries: Mapped[list["Note"]] = relationship(
        "Note", back_populates="application", cascade="all, delete-orphan"
    )
