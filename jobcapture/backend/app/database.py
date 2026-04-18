from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

class Base(DeclarativeBase):
    pass

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        kwargs = {}
        if settings.database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(settings.database_url, **kwargs)
    return _engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal

def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
