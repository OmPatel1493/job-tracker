"""
Resume DB model.

WHY one resume per user (unique user_id):
  A user's profile has one active resume at a time. The upload endpoint
  upserts — it updates the existing record rather than creating duplicates.
  If the user uploads a new file, the old text, skills, and embedding are
  overwritten in place.

WHY store raw_text in the DB (not just the Pinecone vector):
  The vector is useful for similarity search, but raw text is needed for:
  - Re-running skill extraction with an updated prompt
  - Displaying the parsed text back to the user
  - Running comparisons without another Pinecone round-trip

WHY JSON for parsed_skills:
  Skill structure is a dict of lists (e.g. {"languages": ["Python", ...]}).
  MySQL JSON column stores and retrieves this natively without serialisation
  boilerplate in the application layer.
"""

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,   # one resume per user
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_skills: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Resume → User (read-only back-reference, no back_populates needed on User)
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
