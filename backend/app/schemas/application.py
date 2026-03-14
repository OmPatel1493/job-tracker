from datetime import date

from pydantic import BaseModel

from app.models.job_application import ApplicationStatus


class ApplicationCreate(BaseModel):
    company_name: str
    job_title: str
    job_description: str | None = None
    job_url: str | None = None
    location: str | None = None
    is_remote: bool = False
    status: ApplicationStatus = ApplicationStatus.APPLIED
    application_date: date | None = None
    salary_min: int | None = None
    salary_max: int | None = None


class ApplicationUpdate(BaseModel):
    company_name: str | None = None
    job_title: str | None = None
    job_description: str | None = None
    job_url: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    status: ApplicationStatus | None = None
    application_date: date | None = None
    salary_min: int | None = None
    salary_max: int | None = None


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    company_name: str
    job_title: str
    job_description: str | None
    job_url: str | None
    location: str | None
    is_remote: bool
    status: ApplicationStatus
    application_date: date | None
    salary_min: int | None
    salary_max: int | None

    model_config = {"from_attributes": True}
