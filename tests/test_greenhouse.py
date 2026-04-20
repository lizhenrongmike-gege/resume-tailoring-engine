#!/usr/bin/env python3
"""Tests for Greenhouse connector."""
import json
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.greenhouse import GreenhouseConnector
from jobscan.connectors.base import RawPosting


SAMPLE_GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "title": "Fraud Analyst",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
            "content": "<p>Investigate fraud patterns using SQL...</p>",
            "updated_at": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S-05:00"),
            "departments": [{"id": 1, "name": "Risk"}],
        },
        {
            "title": "Senior Software Engineer",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/456",
            "content": "<p>Build distributed systems...</p>",
            "updated_at": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S-05:00"),
        },
        {
            "title": "Old Role",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/789",
            "content": "<p>Something from long ago...</p>",
            "updated_at": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S-05:00"),
        },
    ]
}


@patch("jobscan.connectors.greenhouse.requests.get")
def test_fetch_returns_raw_postings(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GREENHOUSE_RESPONSE
    mock_get.return_value = mock_resp

    conn = GreenhouseConnector()
    results = conn.fetch_company("stripe", "Stripe", days_back=7)

    assert len(results) == 2  # old role filtered by date
    assert all(isinstance(r, RawPosting) for r in results)
    assert results[0].source == "greenhouse"
    assert results[0].company == "Stripe"


@patch("jobscan.connectors.greenhouse.requests.get")
def test_fetch_handles_api_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    conn = GreenhouseConnector()
    results = conn.fetch_company("nonexistent", "Nobody", days_back=7)
    assert results == []


@patch("jobscan.connectors.greenhouse.requests.get")
def test_department_extracted(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GREENHOUSE_RESPONSE
    mock_get.return_value = mock_resp
    conn = GreenhouseConnector()
    results = conn.fetch_company("stripe", "Stripe", days_back=7)
    assert results[0].department == "Risk"


@patch("jobscan.connectors.greenhouse.requests.get")
def test_html_stripped_from_description(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GREENHOUSE_RESPONSE
    mock_get.return_value = mock_resp

    conn = GreenhouseConnector()
    results = conn.fetch_company("stripe", "Stripe", days_back=7)
    for r in results:
        assert "<p>" not in r.description
        assert "</p>" not in r.description
