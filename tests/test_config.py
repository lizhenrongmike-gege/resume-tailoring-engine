#!/usr/bin/env python3
"""Tests for jobscan config: lanes, companies, filter patterns."""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.config import (
    LANES,
    PRIORITY_COMPANIES,
    SENIORITY_PATTERN,
    YOE_PATTERN,
    EXCLUDED_TITLES,
    LOCATION_ALLOW_PATTERN,
)


def test_four_lanes_defined():
    assert len(LANES) == 4
    assert all(lane["id"] in (1, 2, 3, 4) for lane in LANES)


def test_lane_has_required_fields():
    for lane in LANES:
        assert "id" in lane
        assert "name" in lane
        assert "acceptable_titles" in lane
        assert "search_keywords" in lane
        assert len(lane["acceptable_titles"]) > 0
        assert len(lane["search_keywords"]) > 0


def test_priority_companies_structure():
    assert len(PRIORITY_COMPANIES) > 0
    for co in PRIORITY_COMPANIES:
        assert "name" in co
        assert "ats" in co
        assert co["ats"] in ("greenhouse", "lever", "ashby", "unknown")
        assert "slug" in co


def test_seniority_pattern_matches():
    for title in ["Senior Fraud Analyst", "Staff Engineer", "Lead Risk Analyst",
                   "VP of Operations", "Director of Trust", "Head of Fraud",
                   "Principal Engineer", "Manager, Risk Ops"]:
        assert re.search(SENIORITY_PATTERN, title, re.IGNORECASE), f"Should match: {title}"


def test_seniority_pattern_skips_clean_titles():
    for title in ["Fraud Analyst", "Risk Operations Analyst",
                   "Implementation Engineer", "GTM Engineer"]:
        assert not re.search(SENIORITY_PATTERN, title, re.IGNORECASE), f"Should NOT match: {title}"


def test_yoe_pattern_catches_high_experience():
    for text in ["4+ years of experience", "5 years experience required",
                  "10+ years in fraud", "7-10 years of relevant experience"]:
        assert re.search(YOE_PATTERN, text, re.IGNORECASE), f"Should match: {text}"


def test_yoe_pattern_allows_low_experience():
    for text in ["1+ years of experience", "2 years experience",
                  "3 years of relevant experience", "0-2 years"]:
        assert not re.search(YOE_PATTERN, text, re.IGNORECASE), f"Should NOT match: {text}"


def test_excluded_titles():
    assert "Software Engineer" in EXCLUDED_TITLES
    assert "ML Engineer" in EXCLUDED_TITLES
    assert "Data Scientist" in EXCLUDED_TITLES
    assert "Research Scientist" in EXCLUDED_TITLES
    assert "Forward Deployed Engineer" in EXCLUDED_TITLES


def test_location_allow_pattern():
    for loc in ["San Francisco, CA", "SF Bay Area", "Remote",
                "San Jose, CA", "Palo Alto, CA", "Oakland, CA",
                "Mountain View, CA", "Anywhere", "Remote US",
                "United States (Remote)"]:
        assert re.search(LOCATION_ALLOW_PATTERN, loc, re.IGNORECASE), f"Should allow: {loc}"
