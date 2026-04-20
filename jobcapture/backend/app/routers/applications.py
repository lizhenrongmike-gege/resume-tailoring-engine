import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services import company_matcher

_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug format")


router = APIRouter(prefix="/api/applications", tags=["applications"])


class CompanyMatch(BaseModel):
    method: str
    summary_file: str
    jd_file: str | None = None
    script_file: str


class QuestionItem(BaseModel):
    id: str
    text: str
    field_selector: str
    char_limit: int | None = None
    word_limit: int | None = None
    field_type: str


class QuestionsPayload(BaseModel):
    company: str
    role: str
    application_url: str
    company_match: CompanyMatch
    questions: list[QuestionItem]


def _slug_has_outputs(slug: str) -> bool:
    summary = settings.output_summaries_dir / f"{slug}.yaml"
    script = settings.output_scripts_dir / f"generate_{slug}_resume.js"
    return summary.exists() and script.exists()


@router.post("/{company_slug}/questions", status_code=201)
def post_questions(company_slug: str, payload: QuestionsPayload) -> dict:
    _validate_slug(company_slug)
    if not _slug_has_outputs(company_slug):
        raise HTTPException(status_code=404, detail=f"No tailored outputs for slug '{company_slug}'")

    apps_dir: Path = settings.output_applications_dir
    apps_dir.mkdir(parents=True, exist_ok=True)

    record = payload.model_dump()
    record["captured_at"] = datetime.now(timezone.utc).isoformat()

    target = apps_dir / f"{company_slug}_questions.json"
    target.write_text(json.dumps(record, indent=2))
    return {"slug": company_slug, "path": str(target)}


# Literal paths (/pending, /match) must be declared before /{company_slug}/* routes.
@router.get("/pending")
def list_pending() -> list[dict]:
    apps_dir: Path = settings.output_applications_dir
    if not apps_dir.exists():
        return []
    pending: list[dict] = []
    for q in sorted(apps_dir.glob("*_questions.json")):
        slug = q.name.removesuffix("_questions.json")
        answers = apps_dir / f"{slug}_answers.json"
        if answers.exists():
            continue
        pending.append({"slug": slug, "questions_file": str(q)})
    return pending


@router.get("/match")
def match_company(company: str) -> dict:
    candidates = company_matcher.find_candidates(company)
    if len(candidates) == 1:
        return {"method": "auto", "candidates": candidates}
    if len(candidates) > 1:
        return {"method": "ambiguous", "candidates": candidates}
    return {"method": "none", "candidates": []}


@router.get("/{company_slug}/answers")
def get_answers(company_slug: str) -> dict:
    _validate_slug(company_slug)
    path = settings.output_applications_dir / f"{company_slug}_answers.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No answers for slug '{company_slug}'")
    return json.loads(path.read_text())
