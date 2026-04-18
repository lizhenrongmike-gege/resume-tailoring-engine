import uuid
from datetime import datetime
from pydantic import BaseModel

class JobCreate(BaseModel):
    company: str
    title: str
    description: str | None = None
    application_url: str | None = None
    company_url: str | None = None
    location: str | None = None
    team: str | None = None
    source_site: str | None = None

class JobUpdate(BaseModel):
    status: str | None = None
    team: str | None = None
    notes: str | None = None

class JobResponse(BaseModel):
    id: uuid.UUID
    company: str
    title: str
    description: str | None
    application_url: str | None
    company_url: str | None
    location: str | None
    team: str | None
    source_site: str | None
    status: str
    batch_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    applied_at: datetime
    resume_version: str | None
    notes: str | None
    outcome: str | None
    job: JobResponse | None = None

    class Config:
        from_attributes = True

class HistoryUpdate(BaseModel):
    outcome: str | None = None
    notes: str | None = None

class BatchFinishResponse(BaseModel):
    batch_id: uuid.UUID
    jobs_count: int
    export_ready: bool
