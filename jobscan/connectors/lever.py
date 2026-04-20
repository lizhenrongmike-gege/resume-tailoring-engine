"""Lever public postings API connector."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from jobscan.connectors.base import BaseConnector, RawPosting

logger = logging.getLogger(__name__)


class LeverConnector(BaseConnector):
    BASE_URL = "https://api.lever.co/v0/postings/{slug}"

    def fetch_company(self, slug: str, company_name: str, days_back: int = 7) -> list[RawPosting]:
        url = self.BASE_URL.format(slug=slug)
        try:
            resp = requests.get(url, timeout=15)
        except requests.RequestException as e:
            logger.warning("Lever request failed for %s: %s", slug, e)
            return []

        if resp.status_code != 200:
            logger.warning("Lever returned %d for %s", resp.status_code, slug)
            return []

        data = resp.json()
        if not isinstance(data, list):
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        results = []

        for posting in data:
            created_ms = posting.get("createdAt", 0)
            posted = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)

            if posted < cutoff:
                continue

            categories = posting.get("categories", {})
            dept = categories.get("team") or categories.get("department") or ""
            results.append(RawPosting(
                title=posting.get("text", ""),
                company=company_name,
                location=categories.get("location", ""),
                description=posting.get("descriptionPlain", ""),
                url=posting.get("hostedUrl", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="lever",
                department=dept,
            ))

        return results

    def search(self, keywords: list[str], location: str, days_back: int = 7) -> list[RawPosting]:
        raise NotImplementedError("Lever has no global search. Use fetch_company per company.")
