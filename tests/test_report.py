#!/usr/bin/env python3
"""Tests for markdown report generation."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.base import RawPosting
from jobscan.ranker import RankedJob
from jobscan.report import generate_report


def _ranked_job(lane=1, fit_score=80, company="Stripe", title="Fraud Analyst",
                location="SF, CA", posted_date="2026-04-05") -> RankedJob:
    return RankedJob(
        posting=RawPosting(
            title=title, company=company, location=location,
            description="Full JD text here...", url="https://example.com/1",
            posted_date=posted_date, source="greenhouse",
        ),
        lane=lane, fit_score=fit_score, title_clean=title,
        why_it_fits="Strong KYC match from prior risk-ops experience.",
        disqualifiers=[], subtle_flags=["2+ years preferred"],
        sponsorship_signal="unknown", preference_score=3,
        preference_reasons=["mentions SQL"],
    )


def test_report_has_summary_section():
    md = generate_report(ranked_jobs=[_ranked_job()], repeats=[])
    assert "## Summary" in md
    assert "Total new roles: 1" in md


def test_report_has_lane_sections():
    jobs = [
        _ranked_job(lane=1, company="Stripe", title="Fraud Analyst"),
        _ranked_job(lane=3, company="Pinecone", title="Solutions Engineer"),
    ]
    md = generate_report(ranked_jobs=jobs, repeats=[])
    assert "## Lane 1" in md
    assert "## Lane 3" in md
    assert "Stripe" in md
    assert "Pinecone" in md


def test_report_has_role_details():
    md = generate_report(ranked_jobs=[_ranked_job()], repeats=[])
    assert "**Location:**" in md
    assert "**Posted:**" in md
    assert "**Why it fits:**" in md
    assert "**Apply:**" in md


def test_report_has_repeats_section():
    repeats = [{"company": "Adyen", "title": "Risk Analyst", "run_count": 3,
                "first_seen": "2026-04-01"}]
    md = generate_report(ranked_jobs=[], repeats=repeats)
    assert "Repeats" in md
    assert "Adyen" in md


def test_report_top_recommendation():
    jobs = [
        _ranked_job(lane=1, fit_score=90, company="Stripe", title="Fraud Analyst"),
        _ranked_job(lane=2, fit_score=70, company="DoorDash", title="Data Analyst"),
    ]
    md = generate_report(ranked_jobs=jobs, repeats=[])
    assert "Top recommendation:" in md
    assert "Stripe" in md


def test_empty_report():
    md = generate_report(ranked_jobs=[], repeats=[])
    assert "Total new roles: 0" in md
