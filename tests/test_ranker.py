#!/usr/bin/env python3
"""Tests for Sonnet ranker module."""
import json
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.connectors.base import RawPosting
from jobscan.ranker import SonnetRanker, RankedJob, build_ranking_prompt


def _posting(**overrides) -> RawPosting:
    defaults = dict(
        title="Fraud Analyst", company="Stripe", location="San Francisco, CA",
        description="Investigate fraud patterns using SQL. KYC experience preferred.",
        url="https://example.com/1", posted_date="2026-04-05", source="greenhouse",
    )
    defaults.update(overrides)
    return RawPosting(**defaults)


def test_build_ranking_prompt_includes_profile():
    prompt = build_ranking_prompt(
        postings=[_posting()],
        profile_facts="name: Test User\neducation: BC",
        profile_evidence="lane_1:\n  keywords: [KYC, SQL]",
    )
    assert "Test User" in prompt
    assert "KYC" in prompt
    assert "Fraud Analyst" in prompt
    assert "Stripe" in prompt


def test_build_ranking_prompt_includes_all_postings():
    postings = [
        _posting(title="Fraud Analyst", company="Stripe"),
        _posting(title="Risk Analyst", company="Adyen"),
    ]
    prompt = build_ranking_prompt(postings=postings, profile_facts="...", profile_evidence="...")
    assert "Fraud Analyst" in prompt
    assert "Risk Analyst" in prompt
    assert "Stripe" in prompt
    assert "Adyen" in prompt


def test_ranked_job_dataclass():
    job = RankedJob(
        posting=_posting(),
        lane=1, fit_score=82, title_clean="Fraud Analyst",
        why_it_fits="KYC maps directly.", disqualifiers=[],
        subtle_flags=["2+ years preferred"],
        sponsorship_signal="unknown",
        preference_score=3,
        preference_reasons=["posted 2 days ago"],
    )
    assert job.fit_score == 82
    assert job.lane == 1


MOCK_SONNET_RESPONSE = json.dumps([
    {
        "index": 0,
        "lane": 1,
        "fit_score": 82,
        "title_clean": "Fraud Analyst",
        "why_it_fits": "Strong KYC/SQL match from prior risk-ops role.",
        "disqualifiers": [],
        "subtle_flags": [],
        "sponsorship_signal": "unknown",
        "preference_score": 3,
        "preference_reasons": ["mentions SQL"],
    }
])


@patch("jobscan.ranker.anthropic")
def test_rank_postings_returns_ranked_jobs(mock_anthropic):
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_block = MagicMock()
    mock_block.text = MOCK_SONNET_RESPONSE
    mock_msg.content = [mock_block]
    mock_client.messages.create.return_value = mock_msg
    mock_anthropic.Anthropic.return_value = mock_client

    ranker = SonnetRanker(api_key="test-key")
    results = ranker.rank_postings([_posting()])

    assert len(results) == 1
    assert results[0].fit_score == 82
    assert results[0].lane == 1
