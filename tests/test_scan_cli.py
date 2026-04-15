#!/usr/bin/env python3
"""Tests for scan.py CLI entry point."""
import os
import subprocess
import sys
import tempfile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "jobscan", "scan.py")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def run_cli(*args, env_override=None):
    env = os.environ.copy()
    env["JOBSCAN_DB_PATH"] = tempfile.mktemp(suffix=".db")
    env["JOBSCAN_SKIP_SEARCH"] = "1"  # skip actual API calls in tests
    if env_override:
        env.update(env_override)
    result = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )
    return result


def test_help_flag():
    """--help should show usage."""
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "scan" in result.stdout.lower()


def test_history_subcommand():
    """history should run without error on empty db."""
    result = run_cli("history")
    assert result.returncode == 0


def test_export_subcommand_on_empty_db():
    """export should run without error on empty db."""
    result = run_cli("export")
    assert result.returncode == 0


def test_mark_subcommand_missing_args():
    """mark should fail with missing arguments."""
    result = run_cli("mark")
    assert result.returncode != 0
