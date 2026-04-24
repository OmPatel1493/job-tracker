import enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.note import Note
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobApplication(TimestampMixin, Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core job info
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_remote: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Status tracking
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.APPLIED,
        nullable=False,
    )
    application_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    # Compensation
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="application", cascade="all, delete-orphan"
    )
