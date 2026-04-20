import uuid
from pathlib import Path
from pydantic_settings import BaseSettings

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
# Project root is resume_tailoring_skill/, which is two parents up from this file
# (jobcapture/backend/app/config.py → jobcapture/backend → jobcapture → resume_tailoring_skill).
PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobcapture.db"
    default_user_id: uuid.UUID = DEFAULT_USER_ID
    project_root: Path = PROJECT_ROOT
    output_applications_dir: Path = PROJECT_ROOT / "output" / "applications"
    output_summaries_dir: Path = PROJECT_ROOT / "output" / "summaries"
    output_jds_dir: Path = PROJECT_ROOT / "output" / "jds"
    output_scripts_dir: Path = PROJECT_ROOT / "output" / "scripts"

    class Config:
        env_file = ".env"

settings = Settings()
