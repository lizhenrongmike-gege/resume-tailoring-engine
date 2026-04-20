import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import Job
from app.services.excel_export import generate_batch_xlsx

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/batch_jds")
def export_batch_jds(batch_id: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Job).filter(Job.user_id == settings.default_user_id)

    if batch_id:
        query = query.filter(Job.batch_id == _uuid.UUID(batch_id))
    elif status:
        query = query.filter(Job.status == status)
    else:
        # Default: export active batch jobs
        query = query.filter(Job.status == "active_batch")

    jobs = query.all()
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs to export")

    job_dicts = [
        {
            "company": j.company,
            "description": j.description or "",
            "url": j.application_url or "",
            "company_url": j.company_url or "",
            "location": j.location or "",
        }
        for j in jobs
    ]

    buffer = generate_batch_xlsx(job_dicts)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=batch_jds.xlsx"},
    )
