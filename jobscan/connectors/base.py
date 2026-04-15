"""Base connector interface and shared data types."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawPosting:
    """A job posting as returned by any connector."""
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: str | None
    source: str


class BaseConnector:
    """Abstract connector interface. All tiers implement this."""

    def search(
        self,
        keywords: list[str],
        location: str,
        days_back: int = 7,
    ) -> list[RawPosting]:
        raise NotImplementedError
