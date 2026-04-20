from pathlib import Path
import re

from app.config import settings


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _slug_matches_company(slug: str, company_norm: str) -> bool:
    # Variant suffix like "_2" — strip to compare against the base company name.
    base = re.sub(r"_\d+$", "", slug)
    return _normalize(base) == company_norm


def find_candidates(company_name: str) -> list[dict]:
    """Return a list of candidate slugs whose outputs exist on disk.

    Each candidate dict carries absolute paths to the summary, JD, and script files
    (JD file is optional — may not exist for every slug).
    """
    if not company_name or not company_name.strip():
        return []

    target = _normalize(company_name)
    summaries_dir: Path = settings.output_summaries_dir
    scripts_dir: Path = settings.output_scripts_dir
    jds_dir: Path = settings.output_jds_dir

    if not summaries_dir.exists():
        return []

    candidates: list[dict] = []
    for summary_path in sorted(summaries_dir.glob("*.yaml")):
        slug = summary_path.stem
        if not _slug_matches_company(slug, target):
            continue
        script_path = scripts_dir / f"generate_{slug}_resume.js"
        if not script_path.exists():
            continue
        jd_path = jds_dir / f"{slug}.txt"
        candidates.append({
            "slug": slug,
            "summary_file": str(summary_path),
            "jd_file": str(jd_path) if jd_path.exists() else None,
            "script_file": str(script_path),
        })
    return candidates
