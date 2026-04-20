"""Greenhouse public board API connector."""
from __future__ import annotations

import html as html_mod
import re
import logging
from datetime import datetime, timedelta, timezone

import requests

from jobscan.connectors.base import BaseConnector, RawPosting

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    # Decode HTML entities first (&lt;p&gt; → <p>), then strip tags
    decoded = html_mod.unescape(raw)
    text = _HTML_TAG_RE.sub(" ", decoded)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class GreenhouseConnector(BaseConnector):
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

    def fetch_company(self, slug: str, company_name: str, days_back: int = 7) -> list[RawPosting]:
        url = self.BASE_URL.format(slug=slug) + "?content=true"
        try:
            resp = requests.get(url, timeout=15)
        except requests.RequestException as e:
            logger.warning("Greenhouse request failed for %s: %s", slug, e)
            return []

        if resp.status_code != 200:
            logger.warning("Greenhouse returned %d for %s", resp.status_code, slug)
            return []

        data = resp.json()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        results = []

        for job in data.get("jobs", []):
            posted = _parse_date(job.get("updated_at", ""))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)

            if posted < cutoff:
                continue

            depts = job.get("departments") or []
            dept = ", ".join(d.get("name", "") for d in depts if d.get("name"))

            results.append(RawPosting(
                title=job.get("title", ""),
                company=company_name,
                location=job.get("location", {}).get("name", ""),
                description=_strip_html(job.get("content", "")),
                url=job.get("absolute_url", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="greenhouse",
                department=dept,
            ))

        return results

    def search(self, keywords: list[str], location: str, days_back: int = 7) -> list[RawPosting]:
        raise NotImplementedError("Greenhouse has no global search. Use fetch_company per company.")
