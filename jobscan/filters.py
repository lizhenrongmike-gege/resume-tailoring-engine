"""Hard filter rules applied before LLM ranking."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobscan.connectors.base import RawPosting
from jobscan.config import (
    SENIORITY_PATTERN, YOE_PATTERN, EXCLUDED_TITLES, LOCATION_ALLOW_PATTERN,
    POSITIVE_TITLE_KEYWORDS,
)

_CUSTOMER_SIGNALS = re.compile(
    r"(?:customer|client|implementation|solutions|integration|onboard|post-sales)",
    re.IGNORECASE,
)


@dataclass
class FilterResult:
    passed: list[RawPosting] = field(default_factory=list)
    failed: list[RawPosting] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)


def _check_posting(posting: RawPosting) -> str | None:
    title = posting.title

    title_lower = title.lower()
    if not any(kw.lower() in title_lower for kw in POSITIVE_TITLE_KEYWORDS):
        return "No positive title keyword match"

    if re.search(SENIORITY_PATTERN, title, re.IGNORECASE):
        return "Seniority filter: title contains seniority keyword"

    title_lower = title.strip().lower()
    for excluded in EXCLUDED_TITLES:
        if excluded.lower() in title_lower:
            return f"Excluded title: {excluded}"

    # Check for pure AI Engineer (no customer-facing signals)
    if re.search(r"AI\s+Engineer", title, re.IGNORECASE):
        if not _CUSTOMER_SIGNALS.search(posting.description):
            return "Pure AI Engineer with no customer-facing signal"

    if not re.search(LOCATION_ALLOW_PATTERN, posting.location, re.IGNORECASE):
        return f"Location not in Bay Area/Remote: {posting.location}"

    if re.search(YOE_PATTERN, posting.description, re.IGNORECASE):
        return "Experience requirement exceeds 3 years"

    return None


def apply_hard_filters(postings: list[RawPosting]) -> FilterResult:
    result = FilterResult()
    for posting in postings:
        reason = _check_posting(posting)
        if reason:
            result.failed.append(posting)
            result.reasons[posting.url] = reason
        else:
            result.passed.append(posting)
    return result
