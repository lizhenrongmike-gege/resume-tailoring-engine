from pathlib import Path

import pytest

from app.services import company_matcher


@pytest.fixture
def fake_output(tmp_path, monkeypatch):
    summaries = tmp_path / "summaries"
    summaries.mkdir()
    (summaries / "glia.yaml").write_text("company: Glia\n")
    (summaries / "composio.yaml").write_text("company: Composio\n")
    (summaries / "composio_2.yaml").write_text("company: Composio\n")

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "generate_glia_resume.js").write_text("")
    (scripts / "generate_composio_resume.js").write_text("")
    (scripts / "generate_composio_2_resume.js").write_text("")

    jds = tmp_path / "jds"
    jds.mkdir()

    from app.config import settings
    monkeypatch.setattr(settings, "output_summaries_dir", summaries)
    monkeypatch.setattr(settings, "output_scripts_dir", scripts)
    monkeypatch.setattr(settings, "output_jds_dir", jds)
    return tmp_path


def test_exact_match_returns_single_candidate(fake_output):
    candidates = company_matcher.find_candidates("Glia")
    assert len(candidates) == 1
    assert candidates[0]["slug"] == "glia"
    assert candidates[0]["summary_file"].endswith("summaries/glia.yaml")
    assert candidates[0]["script_file"].endswith("scripts/generate_glia_resume.js")


def test_multiple_candidates_when_company_has_variants(fake_output):
    candidates = company_matcher.find_candidates("Composio")
    slugs = {c["slug"] for c in candidates}
    assert slugs == {"composio", "composio_2"}


def test_fuzzy_match_is_case_and_whitespace_insensitive(fake_output):
    candidates = company_matcher.find_candidates("  GLIA  ")
    assert len(candidates) == 1
    assert candidates[0]["slug"] == "glia"


def test_no_match_returns_empty_list(fake_output):
    assert company_matcher.find_candidates("NonexistentCorp") == []


def test_missing_script_file_is_skipped(fake_output, tmp_path):
    (tmp_path / "summaries" / "orphan.yaml").write_text("company: Orphan\n")
    candidates = company_matcher.find_candidates("Orphan")
    assert candidates == []
