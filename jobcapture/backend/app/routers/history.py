import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.config import settings
from app.models import ApplicationHistory, Job
from app.schemas import HistoryResponse, HistoryUpdate

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("", response_model=list[HistoryResponse])
def list_history(outcome: str | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(ApplicationHistory)
        .options(joinedload(ApplicationHistory.job))
        .filter(ApplicationHistory.user_id == settings.default_user_id)
    )
    if outcome:
        query = query.filter(ApplicationHistory.outcome == outcome)
    return query.order_by(ApplicationHistory.applied_at.desc()).all()

@router.patch("/{entry_id}", response_model=HistoryResponse)
def update_history(entry_id: uuid.UUID, payload: HistoryUpdate, db: Session = Depends(get_db)):
    entry = db.query(ApplicationHistory).filter(ApplicationHistory.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry
