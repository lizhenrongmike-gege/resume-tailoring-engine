import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import Job, ApplicationHistory
from app.schemas import BatchFinishResponse

router = APIRouter(prefix="/api/batches", tags=["batches"])

@router.post("/finish", response_model=BatchFinishResponse)
def finish_batch(db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.user_id == settings.default_user_id, Job.status == "active_batch")
        .all()
    )
    if not jobs:
        raise HTTPException(status_code=400, detail="No jobs in active batch")

    batch_id = uuid.uuid4()

    for job in jobs:
        job.status = "applied"
        job.batch_id = batch_id
        db.add(ApplicationHistory(
            job_id=job.id,
            user_id=job.user_id,
        ))

    db.commit()
    return BatchFinishResponse(
        batch_id=batch_id,
        jobs_count=len(jobs),
        export_ready=True,
    )
