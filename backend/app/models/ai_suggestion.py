"""
AiSuggestion DB model.

Stores the AI-generated resume suggestions for a job application.
One record per application - re-generating overwrites the existing row.

WHY store suggestions as a JSON string (Text column):
    The suggestions list is a list of dicts with a fixed shape. Storing
    as a JSON string keeps the model simple and avoids a separate
    suggestions_items table. The router deserialises with json.loads()
    before returning to the client.

WHY cascade delete:
    Suggestions are meaningless without their parent application. When
    an application is deleted, its suggestions row is cleaned up automatically.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AiSuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    application: Mapped["JobApplication"] = relationship("JobApplication")  # type: ignore[name-defined]
