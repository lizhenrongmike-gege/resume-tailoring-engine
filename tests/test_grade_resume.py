#!/usr/bin/env python3
"""Tests for grade_resume.py."""
import json
import os
import subprocess
import sys
import tempfile

import yaml

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "grade_resume.py")
FIXTURE_JS = os.path.join(os.path.dirname(__file__), "fixtures", "sample_resume_content.js")
FIXTURE_KEYWORDS = os.path.join(os.path.dirname(__file__), "fixtures", "sample_keywords.yaml")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def run_grader(js_path, keywords_path, output_path=None):
    cmd = [sys.executable, SCRIPT, js_path, keywords_path]
    if output_path:
        cmd.extend(["--output", output_path])
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    return result


def load_grade(path):
    with open(path) as f:
        return yaml.safe_load(f)


# ── Tests ─────────────────────────────────────────────────────


def test_basic_execution():
    """Grader should run successfully on fixture files."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        result = run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert os.path.exists(output_path), "Grade file not created"
        grade = load_grade(output_path)
        assert grade is not None, "Grade file is empty"
        assert "dimensions" in grade, "Missing dimensions key"
    finally:
        os.unlink(output_path)


def test_bullet_count():
    """Fixture has 14 bullets across 4 items — should score well."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        bs = grade["dimensions"]["bullet_structure"]
        assert bs["total_bullets"] == 14, f"Expected 14 bullets, got {bs['total_bullets']}"
        assert bs["total_items"] == 4, f"Expected 4 items, got {bs['total_items']}"
        assert bs["score"] >= 80, f"Expected high score, got {bs['score']}"
    finally:
        os.unlink(output_path)


def test_bullet_length_classification():
    """All fixture bullets should be within 15-36 word range."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        bl = grade["dimensions"]["bullet_length"]
        dist = bl["distribution"]
        assert dist["violation"] == 0, f"Expected no violations, got {dist['violation']}"
        total = dist["short"] + dist["standard"] + dist["long"] + dist["violation"]
        assert total == 14, f"Distribution should sum to 14, got {total}"
    finally:
        os.unlink(output_path)


def test_metric_density():
    """Most fixture bullets contain numbers — density should be high."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        md = grade["dimensions"]["metric_density"]
        assert md["percentage"] >= 70, f"Expected >=70% density, got {md['percentage']}"
        assert md["quantified_bullets"] >= 10, f"Expected >=10 quantified, got {md['quantified_bullets']}"
    finally:
        os.unlink(output_path)


def test_keyword_coverage():
    """Fixture keywords: 9 PLACED, 3 MISSING out of 12."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        kc = grade["dimensions"]["keyword_coverage"]
        assert kc["placed"] == 9, f"Expected 9 placed, got {kc['placed']}"
        assert kc["missing"] == 3, f"Expected 3 missing, got {kc['missing']}"
        assert kc["total"] == 12, f"Expected 12 total, got {kc['total']}"
        assert kc["hard_req_placed"] == 5, f"Expected 5 hard_req placed, got {kc['hard_req_placed']}"
        assert kc["hard_req_total"] == 6, f"Expected 6 hard_req total, got {kc['hard_req_total']}"
    finally:
        os.unlink(output_path)


def test_verb_quality():
    """Fixture uses varied verbs, none banned — should score 100."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        vq = grade["dimensions"]["verb_quality"]
        assert vq["score"] == 100, f"Expected 100, got {vq['score']}"
        assert len(vq["banned_found"]) == 0, f"Found banned verbs: {vq['banned_found']}"
        assert len(vq["repeated_verbs"]) == 0, f"Found repeated verbs: {vq['repeated_verbs']}"
    finally:
        os.unlink(output_path)


def test_summary_length():
    """Fixture summary is under 45 words."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        sl = grade["dimensions"]["summary_length"]
        assert sl["word_count"] <= 45, f"Summary too long: {sl['word_count']} words"
        assert sl["score"] == 100, f"Expected 100, got {sl['score']}"
    finally:
        os.unlink(output_path)


def test_agent_dimensions_null():
    """Agent-scored dimensions should be null (unfilled)."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        grade = load_grade(output_path)
        for dim in ["xyz_formula", "keyword_contextual_placement", "summary_quality", "reframing_integrity"]:
            assert grade["dimensions"][dim] is None, f"Expected {dim} to be null, got {grade['dimensions'][dim]}"
    finally:
        os.unlink(output_path)


def test_output_summary_line():
    """Script should print a summary line to stdout."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        output_path = tmp.name
    try:
        result = run_grader(FIXTURE_JS, FIXTURE_KEYWORDS, output_path)
        assert "Grade:" in result.stdout, f"Expected summary line, got: {result.stdout}"
        assert "Bullets:" in result.stdout, f"Expected bullet score in summary"
    finally:
        os.unlink(output_path)


def test_invalid_js_file():
    """Should exit with error for non-existent JS file."""
    result = run_grader("/nonexistent/file.js", FIXTURE_KEYWORDS)
    assert result.returncode != 0, "Expected non-zero exit code for missing file"


# ── Runner ────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_basic_execution,
        test_bullet_count,
        test_bullet_length_classification,
        test_metric_density,
        test_keyword_coverage,
        test_verb_quality,
        test_summary_length,
        test_agent_dimensions_null,
        test_output_summary_line,
        test_invalid_js_file,
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
