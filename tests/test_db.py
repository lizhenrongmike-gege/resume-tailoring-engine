#!/usr/bin/env python3
"""Tests for SQLite database and dedup logic."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.db import JobScanDB


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = JobScanDB(db_path)
    yield database
    database.close()
    os.unlink(db_path)


def test_insert_and_retrieve(db):
    db.insert_job(
        company="Stripe", title="Fraud Analyst", lane=1, fit_score=85,
        why_it_fits="Strong KYC match", url="https://example.com/1",
        location="SF, CA", description="Investigate fraud...",
        source="greenhouse",
    )
    jobs = db.get_jobs(status="new")
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Stripe"
    assert jobs[0]["fit_score"] == 85


def test_dedup_returns_true_for_seen(db):
    db.insert_job(
        company="Stripe", title="Fraud Analyst", lane=1, fit_score=80,
        why_it_fits="...", url="https://x.com", location="SF",
        description="...", source="greenhouse",
    )
    assert db.is_seen("Stripe", "Fraud Analyst") is True
    assert db.is_seen("Stripe", "Risk Analyst") is False


def test_touch_updates_last_seen_and_count(db):
    db.insert_job(
        company="Stripe", title="Fraud Analyst", lane=1, fit_score=80,
        why_it_fits="...", url="https://x.com", location="SF",
        description="...", source="greenhouse",
    )
    job_before = db.get_jobs()[0]
    assert job_before["run_count"] == 1
    db.touch_job("Stripe", "Fraud Analyst")
    job_after = db.get_jobs()[0]
    assert job_after["run_count"] == 2


def test_update_status(db):
    db.insert_job(
        company="Stripe", title="Fraud Analyst", lane=1, fit_score=80,
        why_it_fits="...", url="https://x.com", location="SF",
        description="...", source="greenhouse",
    )
    db.mark_status("Stripe", "Fraud Analyst", "applied")
    jobs = db.get_jobs(status="applied")
    assert len(jobs) == 1


def test_get_jobs_by_lane(db):
    db.insert_job(company="A", title="T1", lane=1, fit_score=80,
                  why_it_fits="...", url="u1", location="SF",
                  description="...", source="greenhouse")
    db.insert_job(company="B", title="T2", lane=2, fit_score=70,
                  why_it_fits="...", url="u2", location="SF",
                  description="...", source="lever")
    assert len(db.get_jobs(lane=1)) == 1
    assert len(db.get_jobs(lane=2)) == 1


def test_get_repeats(db):
    db.insert_job(company="A", title="T1", lane=1, fit_score=80,
                  why_it_fits="...", url="u1", location="SF",
                  description="...", source="greenhouse")
    db.touch_job("A", "T1")
    repeats = db.get_repeats()
    assert len(repeats) == 1
    assert repeats[0]["run_count"] == 2


def test_record_run(db):
    db.record_run(new_roles=5, repeat_roles=3, filtered_out=20,
                  lanes_summary={"1": 3, "2": 1, "3": 1, "4": 0})
    runs = db.get_runs()
    assert len(runs) == 1
    assert runs[0]["new_roles"] == 5


def test_unique_constraint(db):
    db.insert_job(company="A", title="T1", lane=1, fit_score=80,
                  why_it_fits="...", url="u1", location="SF",
                  description="...", source="greenhouse")
    with pytest.raises(Exception):
        db.insert_job(company="A", title="T1", lane=1, fit_score=80,
                      why_it_fits="...", url="u1", location="SF",
                      description="...", source="greenhouse")
