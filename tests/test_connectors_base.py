#!/usr/bin/env python3
"""Tests for base connector interface and RawPosting dataclass."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.base import RawPosting, BaseConnector


def test_raw_posting_creation():
    """RawPosting should store all fields."""
    p = RawPosting(
        title="Fraud Analyst",
        company="Stripe",
        location="San Francisco, CA",
        description="Investigate fraud patterns...",
        url="https://boards.greenhouse.io/stripe/jobs/123",
        posted_date="2026-04-05",
        source="greenhouse",
    )
    assert p.title == "Fraud Analyst"
    assert p.company == "Stripe"
    assert p.source == "greenhouse"


def test_raw_posting_optional_posted_date():
    """posted_date should accept None."""
    p = RawPosting(
        title="Risk Analyst", company="Adyen", location="SF",
        description="...", url="https://example.com",
        posted_date=None, source="websearch",
    )
    assert p.posted_date is None


def test_base_connector_not_implemented():
    """BaseConnector.search should raise NotImplementedError."""
    c = BaseConnector()
    with pytest.raises(NotImplementedError):
        c.search(keywords=["fraud"], location="SF", days_back=7)


def test_raw_posting_equality():
    """Two RawPostings with same fields should be equal."""
    kwargs = dict(
        title="Fraud Analyst", company="Stripe", location="SF",
        description="...", url="https://x.com", posted_date=None, source="greenhouse",
    )
    assert RawPosting(**kwargs) == RawPosting(**kwargs)


def test_raw_posting_has_department_default():
    from jobscan.connectors.base import RawPosting
    p = RawPosting(
        title="X", company="Y", location="Z",
        description="", url="", posted_date=None, source="test",
    )
    assert p.department == ""


def test_raw_posting_accepts_department():
    from jobscan.connectors.base import RawPosting
    p = RawPosting(
        title="X", company="Y", location="Z",
        description="", url="", posted_date=None, source="test",
        department="Risk",
    )
    assert p.department == "Risk"
