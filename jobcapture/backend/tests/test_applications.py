import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def temp_output_dirs(tmp_path, monkeypatch):
    apps = tmp_path / "applications"
    summaries = tmp_path / "summaries"
    scripts = tmp_path / "scripts"
    jds = tmp_path / "jds"
    for d in (apps, summaries, scripts, jds):
        d.mkdir()

    (summaries / "glia.yaml").write_text("company: Glia\n")
    (scripts / "generate_glia_resume.js").write_text("")
    (jds / "glia.txt").write_text("job description body")

    from app.config import settings
    monkeypatch.setattr(settings, "output_applications_dir", apps)
    monkeypatch.setattr(settings, "output_summaries_dir", summaries)
    monkeypatch.setattr(settings, "output_scripts_dir", scripts)
    monkeypatch.setattr(settings, "output_jds_dir", jds)
    return tmp_path


def test_post_questions_writes_file(client, temp_output_dirs):
    payload = {
        "company": "Glia",
        "role": "Sales Engineer",
        "application_url": "https://jobs.lever.co/glia/abc/apply",
        "company_match": {
            "method": "auto",
            "summary_file": "output/summaries/glia.yaml",
            "jd_file": "output/jds/glia.txt",
            "script_file": "output/scripts/generate_glia_resume.js",
        },
        "questions": [
            {
                "id": "q1",
                "text": "Describe your experience.",
                "field_selector": "#q1",
                "char_limit": None,
                "word_limit": 500,
                "field_type": "long_text",
            },
        ],
    }
    resp = client.post("/api/applications/glia/questions", json=payload)
    assert resp.status_code == 201
    written = temp_output_dirs / "applications" / "glia_questions.json"
    assert written.exists()
    data = json.loads(written.read_text())
    assert data["company"] == "Glia"
    assert data["questions"][0]["id"] == "q1"
    assert "captured_at" in data


def test_get_answers_returns_404_when_missing(client):
    resp = client.get("/api/applications/glia/answers")
    assert resp.status_code == 404


def test_get_answers_returns_json(client, temp_output_dirs):
    answers = {
        "company": "Glia",
        "answers": [{"id": "q1", "field_selector": "#q1", "answer": "hello"}],
    }
    (temp_output_dirs / "applications" / "glia_answers.json").write_text(json.dumps(answers))
    resp = client.get("/api/applications/glia/answers")
    assert resp.status_code == 200
    assert resp.json()["answers"][0]["answer"] == "hello"


def test_match_returns_single_candidate(client, temp_output_dirs):
    resp = client.get("/api/applications/match", params={"company": "Glia"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "auto"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["slug"] == "glia"


def test_match_no_candidates(client):
    resp = client.get("/api/applications/match", params={"company": "NonExistent"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "none"
    assert body["candidates"] == []


def test_pending_lists_questions_without_answers(client, temp_output_dirs):
    apps = temp_output_dirs / "applications"
    (apps / "glia_questions.json").write_text('{"company": "Glia"}')
    (apps / "acme_questions.json").write_text('{"company": "Acme"}')
    (apps / "acme_answers.json").write_text('{"company": "Acme"}')

    resp = client.get("/api/applications/pending")
    assert resp.status_code == 200
    slugs = [p["slug"] for p in resp.json()]
    assert slugs == ["glia"]


def test_post_questions_rejects_unknown_company_slug(client, temp_output_dirs):
    payload = {
        "company": "Mystery",
        "role": "Engineer",
        "application_url": "https://example.com",
        "company_match": {"method": "auto", "summary_file": "", "jd_file": "", "script_file": ""},
        "questions": [],
    }
    resp = client.post("/api/applications/mystery/questions", json=payload)
    assert resp.status_code == 404


def test_post_questions_rejects_invalid_slug(client):
    payload = {
        "company": "Evil",
        "role": "X",
        "application_url": "https://example.com",
        "company_match": {
            "method": "auto",
            "summary_file": "output/summaries/evil.yaml",
            "script_file": "output/scripts/generate_evil_resume.js",
        },
        "questions": [],
    }
    resp = client.post("/api/applications/..evil/questions", json=payload)
    assert resp.status_code == 400


def test_get_answers_rejects_invalid_slug(client):
    resp = client.get("/api/applications/..evil/answers")
    assert resp.status_code == 400
