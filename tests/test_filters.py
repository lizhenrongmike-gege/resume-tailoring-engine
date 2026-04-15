#!/usr/bin/env python3
"""Tests for hard filter rules."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.base import RawPosting
from jobscan.filters import apply_hard_filters, FilterResult


def _posting(**overrides) -> RawPosting:
    defaults = dict(
        title="Fraud Analyst", company="Stripe",
        location="San Francisco, CA",
        description="Investigate fraud. 2+ years experience. SQL required.",
        url="https://example.com/jobs/1",
        posted_date="2026-04-05", source="greenhouse",
    )
    defaults.update(overrides)
    return RawPosting(**defaults)


def test_clean_posting_passes():
    result = apply_hard_filters([_posting()])
    assert len(result.passed) == 1
    assert len(result.failed) == 0


def test_seniority_filter():
    postings = [
        _posting(title="Senior Fraud Analyst"),
        _posting(title="Staff Risk Analyst"),
        _posting(title="Lead Operations Analyst"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 0
    assert len(result.failed) == 3
    assert all("seniority" in r.lower() for r in result.reasons.values())


def test_high_yoe_filter():
    result = apply_hard_filters([
        _posting(description="Requires 5+ years of experience in fraud operations."),
    ])
    assert len(result.passed) == 0
    assert "experience" in list(result.reasons.values())[0].lower()


def test_low_yoe_passes():
    result = apply_hard_filters([
        _posting(description="2+ years of experience in risk operations."),
    ])
    assert len(result.passed) == 1


def test_excluded_title_filter():
    result = apply_hard_filters([
        _posting(title="Software Engineer"),
        _posting(title="ML Engineer"),
        _posting(title="Data Scientist"),
    ])
    assert len(result.passed) == 0


def test_location_filter():
    result = apply_hard_filters([
        _posting(location="New York, NY"),
        _posting(location="Austin, TX"),
    ])
    assert len(result.passed) == 0


def test_bay_area_locations_pass():
    postings = [
        _posting(location="San Francisco, CA"),
        _posting(location="Mountain View, CA"),
        _posting(location="Remote"),
        _posting(location="San Jose, CA"),
        _posting(location="United States (Remote)"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 5


def test_pure_ai_engineer_filter():
    result = apply_hard_filters([
        _posting(title="AI Engineer",
                 description="Build and train ML models. Deploy to production."),
    ])
    assert len(result.passed) == 0


def test_ai_engineer_with_customer_signal_passes():
    result = apply_hard_filters([
        _posting(title="AI Engineer",
                 description="Work with customers to deploy AI solutions. Implementation."),
    ])
    assert len(result.passed) == 1


def test_multiple_filters_reports_first_reason():
    result = apply_hard_filters([
        _posting(title="Senior Software Engineer", location="New York"),
    ])
    assert len(result.passed) == 0
    assert len(result.failed) == 1
