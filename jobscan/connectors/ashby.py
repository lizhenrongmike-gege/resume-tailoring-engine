"""Ashby public posting API connector."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from jobscan.connectors.base import BaseConnector, RawPosting

logger = logging.getLogger(__name__)


class AshbyConnector(BaseConnector):
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

    def fetch_company(self, slug: str, company_name: str, days_back: int = 7) -> list[RawPosting]:
        url = self.BASE_URL.format(slug=slug)
        try:
            resp = requests.post(url, json={}, timeout=15)
        except requests.RequestException as e:
            logger.warning("Ashby request failed for %s: %s", slug, e)
            return []

        if resp.status_code != 200:
            logger.warning("Ashby returned %d for %s", resp.status_code, slug)
            return []

        data = resp.json()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        results = []

        for job in data.get("jobs", []):
            published = job.get("publishedAt", "")
            try:
                posted = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted = datetime.now(timezone.utc)

            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)

            if posted < cutoff:
                continue

            results.append(RawPosting(
                title=job.get("title", ""),
                company=company_name,
                location=job.get("location", ""),
                description=job.get("descriptionPlain", ""),
                url=job.get("jobUrl", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="ashby",
            ))

        return results

    def search(self, keywords: list[str], location: str, days_back: int = 7) -> list[RawPosting]:
        raise NotImplementedError("Ashby has no global search. Use fetch_company per company.")
