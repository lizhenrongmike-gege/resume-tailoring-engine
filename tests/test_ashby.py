#!/usr/bin/env python3
"""Tests for Ashby connector."""
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.ashby import AshbyConnector
from jobscan.connectors.base import RawPosting

_RECENT_ISO = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
_OLD_ISO = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

SAMPLE_ASHBY_RESPONSE = {
    "jobs": [
        {
            "title": "Implementation Engineer",
            "location": "San Francisco, CA",
            "jobUrl": "https://jobs.ashbyhq.com/decagon/abc",
            "descriptionPlain": "Deploy AI solutions for customers...",
            "publishedAt": _RECENT_ISO,
        },
        {
            "title": "Old Role",
            "location": "SF",
            "jobUrl": "https://jobs.ashbyhq.com/decagon/old",
            "descriptionPlain": "Old...",
            "publishedAt": _OLD_ISO,
        },
    ]
}


@patch("jobscan.connectors.ashby.requests.post")
def test_fetch_returns_recent_postings(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_ASHBY_RESPONSE
    mock_post.return_value = mock_resp

    conn = AshbyConnector()
    results = conn.fetch_company("decagon", "Decagon", days_back=7)

    assert len(results) == 1
    assert results[0].title == "Implementation Engineer"
    assert results[0].source == "ashby"


@patch("jobscan.connectors.ashby.requests.post")
def test_fetch_handles_error(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_post.return_value = mock_resp

    conn = AshbyConnector()
    assert conn.fetch_company("bad", "Bad", days_back=7) == []


SAMPLE_ASHBY_WITH_DEPT = {
    "jobs": [
        {
            "title": "Compliance Analyst",
            "location": "San Francisco, CA",
            "jobUrl": "https://jobs.ashbyhq.com/decagon/abc",
            "descriptionPlain": "Compliance work.",
            "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "department": "Legal & Compliance",
        }
    ]
}

@patch("jobscan.connectors.ashby.requests.post")
def test_department_extracted_ashby(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_ASHBY_WITH_DEPT
    mock_post.return_value = mock_resp
    from jobscan.connectors.ashby import AshbyConnector
    results = AshbyConnector().fetch_company("decagon", "Decagon", days_back=7)
    assert results[0].department == "Legal & Compliance"
