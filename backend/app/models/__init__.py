# Import all models here so Alembic can detect them via Base.metadata
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.note import Note
from app.models.resume import Resume
from app.models.user import User

__all__ = ["User", "JobApplication", "ApplicationStatus", "Note", "Resume"]
