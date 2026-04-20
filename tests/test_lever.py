#!/usr/bin/env python3
"""Tests for Lever connector."""
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.lever import LeverConnector
from jobscan.connectors.base import RawPosting

_NOW_MS = int(datetime.now().timestamp() * 1000)
_OLD_MS = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

SAMPLE_LEVER_RESPONSE = [
    {
        "text": "Risk Operations Analyst",
        "categories": {"location": "San Francisco, CA", "team": "Risk"},
        "hostedUrl": "https://jobs.lever.co/plaid/abc123",
        "descriptionPlain": "Review risk alerts using SQL. 2+ years experience.",
        "createdAt": _NOW_MS,
    },
    {
        "text": "Old Posting",
        "categories": {"location": "SF"},
        "hostedUrl": "https://jobs.lever.co/plaid/old",
        "descriptionPlain": "Old...",
        "createdAt": _OLD_MS,
    },
]


@patch("jobscan.connectors.lever.requests.get")
def test_fetch_returns_recent_postings(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_LEVER_RESPONSE
    mock_get.return_value = mock_resp

    conn = LeverConnector()
    results = conn.fetch_company("plaid", "Plaid", days_back=7)

    assert len(results) == 1
    assert results[0].title == "Risk Operations Analyst"
    assert results[0].source == "lever"
    assert results[0].company == "Plaid"


@patch("jobscan.connectors.lever.requests.get")
def test_fetch_handles_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    conn = LeverConnector()
    assert conn.fetch_company("bad", "Bad", days_back=7) == []


SAMPLE_LEVER_WITH_DEPT = [
    {
        "text": "KYC Analyst",
        "categories": {
            "location": "Remote",
            "team": "Risk",
            "department": "Operations",
        },
        "hostedUrl": "https://jobs.lever.co/plaid/xyz",
        "descriptionPlain": "KYC work.",
        "createdAt": int((datetime.now() - timedelta(days=1)).timestamp() * 1000),
    }
]

@patch("jobscan.connectors.lever.requests.get")
def test_department_extracted_lever(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_LEVER_WITH_DEPT
    mock_get.return_value = mock_resp
    from jobscan.connectors.lever import LeverConnector
    results = LeverConnector().fetch_company("plaid", "Plaid", days_back=7)
    # Lever: prefer team, fall back to department
    assert results[0].department == "Risk"
