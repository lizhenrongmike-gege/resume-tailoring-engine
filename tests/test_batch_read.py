#!/usr/bin/env python3
"""Tests for batch_read_excel.py."""
import json
import os
import subprocess
import sys
import tempfile

from openpyxl import Workbook

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "batch_read_excel.py")
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_batch.xlsx")
MANIFEST = os.path.join(os.path.dirname(__file__), "..", "output", "summaries", "manifest.json")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def run_script(xlsx_path):
    result = subprocess.run(
        [sys.executable, SCRIPT, xlsx_path],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    return result


def test_basic_parsing():
    """Script should parse 3 rows and output valid JSON."""
    result = run_script(FIXTURE)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    entries = json.loads(result.stdout)
    assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"


def test_slug_derivation():
    """Slugs should be lowercase with underscores."""
    result = run_script(FIXTURE)
    entries = json.loads(result.stdout)
    slugs = [e["slug"] for e in entries]
    assert "testcorp" in slugs, f"Expected 'testcorp' slug, got {slugs}"
    assert "acme_inc" in slugs, f"Expected 'acme_inc' slug, got {slugs}"


def test_slug_collision():
    """Duplicate company names should get _2 suffix."""
    result = run_script(FIXTURE)
    entries = json.loads(result.stdout)
    slugs = [e["slug"] for e in entries]
    assert "testcorp" in slugs, f"Missing 'testcorp': {slugs}"
    assert "testcorp_2" in slugs, f"Missing 'testcorp_2': {slugs}"


def test_manifest_written():
    """Script should write manifest.json."""
    run_script(FIXTURE)
    assert os.path.exists(MANIFEST), "manifest.json not created"
    with open(MANIFEST) as f:
        manifest = json.load(f)
    assert len(manifest) == 3, f"Manifest should have 3 entries, got {len(manifest)}"


def test_entry_fields():
    """Each entry should have company, slug, row_index, jd_text."""
    result = run_script(FIXTURE)
    entries = json.loads(result.stdout)
    for entry in entries:
        assert "company" in entry, f"Missing 'company': {entry}"
        assert "slug" in entry, f"Missing 'slug': {entry}"
        assert "row_index" in entry, f"Missing 'row_index': {entry}"
        assert "jd_text" in entry, f"Missing 'jd_text': {entry}"
        assert len(entry["jd_text"]) > 0, f"Empty jd_text: {entry}"


def test_file_not_found():
    """Script should exit 1 on missing file."""
    result = run_script("nonexistent.xlsx")
    assert result.returncode == 1


def test_skips_nan_like_company_values():
    """Rows with NaN-like company placeholders should be ignored."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["company", "Job Description Text"])
    worksheet.append(["nan", "Valid JD that should be ignored because company is invalid"])
    worksheet.append(["NaN", "Another JD that should be ignored"])
    worksheet.append([float("nan"), "Float NaN company should be ignored"])
    worksheet.append(["Valid Corp", "Valid JD that should be kept"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
        temp_path = handle.name

    try:
        workbook.save(temp_path)
        result = run_script(temp_path)
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        entries = json.loads(result.stdout)
        assert len(entries) == 1, f"Expected 1 valid entry, got {len(entries)}"
        assert entries[0]["company"] == "Valid Corp", entries
        assert entries[0]["slug"] == "valid_corp", entries
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    tests = [
        test_basic_parsing,
        test_slug_derivation,
        test_slug_collision,
        test_manifest_written,
        test_entry_fields,
        test_file_not_found,
        test_skips_nan_like_company_values,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
