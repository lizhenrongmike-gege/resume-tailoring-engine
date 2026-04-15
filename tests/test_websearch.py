#!/usr/bin/env python3
"""Tests for web search discovery connector."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.websearch import WebSearchConnector, _extract_jd_from_html
from jobscan.connectors.base import RawPosting


def test_extract_jd_from_json_ld():
    """Should extract description from JSON-LD JobPosting schema."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "JobPosting", "title": "Fraud Analyst",
     "description": "Investigate fraud patterns using SQL.",
     "hiringOrganization": {"name": "Acme"},
     "jobLocation": {"address": {"addressLocality": "San Francisco"}}}
    </script>
    </head><body></body></html>
    """
    result = _extract_jd_from_html(html, "https://example.com")
    assert result is not None
    assert "Investigate fraud" in result["description"]
    assert result["title"] == "Fraud Analyst"


def test_extract_jd_from_plain_text_fallback():
    """Should fallback to page text when no JSON-LD."""
    html = """
    <html><body>
    <h1>Risk Operations Analyst</h1>
    <div class="job-description">
    Review risk alerts. Must have SQL skills. 2 years experience.
    </div>
    </body></html>
    """
    result = _extract_jd_from_html(html, "https://example.com")
    assert result is not None
    assert len(result["description"]) > 20


def test_build_search_queries():
    """Should generate queries for each lane and source site."""
    conn = WebSearchConnector(api_key="test")
    queries = conn._build_search_queries(
        keywords=["Fraud Analyst", "Risk Analyst"],
        location="Bay Area",
    )
    assert len(queries) > 0
    assert any("greenhouse" in q for q in queries)
    assert any("Fraud Analyst" in q for q in queries)
