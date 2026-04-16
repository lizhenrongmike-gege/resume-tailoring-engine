# Application Question Answerer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-part system (Chrome extension capture + Claude Code skill) that detects free-text application questions, generates answers from the candidate's tailored resume outputs, and auto-fills the form.

**Architecture:** The extension's existing floating panel (`content.js`) gains a question-detection mode that posts captured questions to a new FastAPI applications router, which writes them to `output/applications/{slug}_questions.json`. The user runs `/answer-questions` in Claude Code; the skill reads the questions plus the company's summary/JD/resume script/career ledger, applies a YAML prompt strategy, and writes `_answers.json` + `_answers.md`. The extension polls the backend for the answers file and injects values into DOM fields.

**Tech Stack:** FastAPI + pydantic (backend), vanilla JS for the Chrome extension (Manifest V3, no bundler), YAML for prompt strategies, pytest with `TestClient` (already wired in `jobcapture/backend/tests/conftest.py`).

---

## Spec Reference

Design doc: `docs/superpowers/specs/2026-04-16-application-question-answerer-design.md`

## File Structure

**Create:**
- `prompts/answer_strategies/default.yaml` — default generation strategy
- `answer-questions/SKILL.md` — Claude Code skill instructions
- `jobcapture/backend/app/services/company_matcher.py` — slug lookup over `output/summaries/` and `output/scripts/`
- `jobcapture/backend/app/routers/applications.py` — 4 endpoints as file relay
- `jobcapture/backend/tests/test_applications.py` — pytest coverage for the router
- `jobcapture/extension/questions.js` — question detection + auto-fill helpers, exposed on `window`

**Modify:**
- `jobcapture/backend/app/config.py` — add `OUTPUT_APPLICATIONS_DIR` path setting pointing at the project's `output/applications/`
- `jobcapture/backend/app/main.py` — register the new router
- `jobcapture/backend/tests/conftest.py` — add a fixture that points the config at a temp directory
- `jobcapture/extension/content.js` — integrate question section + button states into the floating panel
- `jobcapture/extension/manifest.json` — load `questions.js` before `content.js`

**Responsibilities:**
- `questions.js` is pure logic + DOM helpers (no UI chrome). It exports three globals on `window.JC_QUESTIONS`: `detect()`, `fill(answers)`, and `nonQuestionLabelRegex`. `content.js` owns rendering.
- `applications.py` performs only filesystem I/O; no DB tables.
- `company_matcher.py` is pure Python with one entry point: `find_candidates(company_name)`.

---

## Task 1: Default answer strategy file

**Files:**
- Create: `prompts/answer_strategies/default.yaml`

- [ ] **Step 1: Create the strategy file**

Write file `prompts/answer_strategies/default.yaml`:

```yaml
name: default
description: General-purpose application question answerer
guidelines:
  tone: "Confident but not arrogant. First-person. No filler."
  structure: "Lead with the direct answer, then support with specific examples."
  source_priority:
    - submitted_resume
    - jd_keywords
    - career_ledger
rules:
  - "Never fabricate metrics not in the career ledger"
  - "Mirror terminology from the JD, not generic synonyms"
  - "If the resume already covers it, expand — don't contradict"
length_rules:
  with_char_limit: "Stay under 90% of the limit"
  with_word_limit: "Stay under 90% of the limit"
  no_limit_short_text: "2-3 sentences"
  no_limit_long_text: "3-4 paragraphs with concrete examples"
```

- [ ] **Step 2: Verify the YAML parses**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('prompts/answer_strategies/default.yaml'))['name'])"`
Expected: `default`

- [ ] **Step 3: Commit**

```bash
git add prompts/answer_strategies/default.yaml
git commit -m "feat(answer-questions): add default answer strategy"
```

---

## Task 2: Backend config — add output applications dir

**Files:**
- Modify: `jobcapture/backend/app/config.py`

- [ ] **Step 1: Extend the Settings class**

Current file ends at `settings = Settings()` on line 13. Replace the class body with:

```python
import uuid
from pathlib import Path
from pydantic_settings import BaseSettings

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
# Project root is resume_tailoring_skill/, which is two parents up from this file
# (jobcapture/backend/app/config.py → jobcapture/backend → jobcapture → resume_tailoring_skill).
PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobcapture.db"
    default_user_id: uuid.UUID = DEFAULT_USER_ID
    project_root: Path = PROJECT_ROOT
    output_applications_dir: Path = PROJECT_ROOT / "output" / "applications"
    output_summaries_dir: Path = PROJECT_ROOT / "output" / "summaries"
    output_jds_dir: Path = PROJECT_ROOT / "output" / "jds"
    output_scripts_dir: Path = PROJECT_ROOT / "output" / "scripts"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 2: Verify config loads and points at real directories**

Run: `cd jobcapture/backend && python3 -c "from app.config import settings; print(settings.output_applications_dir); assert settings.output_applications_dir.exists()"`
Expected: Prints the absolute path; no AssertionError.

- [ ] **Step 3: Commit**

```bash
git add jobcapture/backend/app/config.py
git commit -m "feat(backend): expose project output directory paths in settings"
```

---

## Task 3: Company matcher service — failing test first

**Files:**
- Test: `jobcapture/backend/tests/test_company_matcher.py`
- Create: `jobcapture/backend/app/services/company_matcher.py` (next task)

- [ ] **Step 1: Write the failing test**

Create `jobcapture/backend/tests/test_company_matcher.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd jobcapture/backend && pytest tests/test_company_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.company_matcher'` (or similar ImportError).

- [ ] **Step 3: Commit the failing test**

```bash
git add jobcapture/backend/tests/test_company_matcher.py
git commit -m "test(company-matcher): specify slug resolution behavior"
```

---

## Task 4: Implement company matcher

**Files:**
- Create: `jobcapture/backend/app/services/company_matcher.py`

- [ ] **Step 1: Write the implementation**

Create `jobcapture/backend/app/services/company_matcher.py`:

```python
from pathlib import Path
import re
import yaml

from app.config import settings


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _slug_matches_company(slug: str, company_norm: str) -> bool:
    # Variant suffix like "_2" — strip to compare against the base company name.
    base = re.sub(r"_\d+$", "", slug)
    return _normalize(base) == company_norm


def find_candidates(company_name: str) -> list[dict]:
    """Return a list of candidate slugs whose outputs exist on disk.

    Each candidate dict carries absolute paths to the summary, JD, and script files
    (JD file is optional — may not exist for every slug).
    """
    if not company_name or not company_name.strip():
        return []

    target = _normalize(company_name)
    summaries_dir: Path = settings.output_summaries_dir
    scripts_dir: Path = settings.output_scripts_dir
    jds_dir: Path = settings.output_jds_dir

    if not summaries_dir.exists():
        return []

    candidates: list[dict] = []
    for summary_path in sorted(summaries_dir.glob("*.yaml")):
        slug = summary_path.stem
        if slug == "manifest":
            continue
        if not _slug_matches_company(slug, target):
            continue
        script_path = scripts_dir / f"generate_{slug}_resume.js"
        if not script_path.exists():
            continue
        jd_path = jds_dir / f"{slug}.txt"
        candidates.append({
            "slug": slug,
            "summary_file": str(summary_path),
            "jd_file": str(jd_path) if jd_path.exists() else None,
            "script_file": str(script_path),
        })
    return candidates
```

- [ ] **Step 2: Run the test**

Run: `cd jobcapture/backend && pytest tests/test_company_matcher.py -v`
Expected: PASS (5 tests).

- [ ] **Step 3: Commit**

```bash
git add jobcapture/backend/app/services/company_matcher.py
git commit -m "feat(company-matcher): resolve company name to existing output slugs"
```

---

## Task 5: Applications router — failing tests first

**Files:**
- Test: `jobcapture/backend/tests/test_applications.py`

- [ ] **Step 1: Write the failing tests**

Create `jobcapture/backend/tests/test_applications.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd jobcapture/backend && pytest tests/test_applications.py -v`
Expected: FAIL — router doesn't exist; most likely `404` or module import error from `main.py`.

- [ ] **Step 3: Commit the failing test**

```bash
git add jobcapture/backend/tests/test_applications.py
git commit -m "test(applications): specify file-relay endpoints"
```

---

## Task 6: Implement applications router

**Files:**
- Create: `jobcapture/backend/app/routers/applications.py`

- [ ] **Step 1: Write the router**

Create `jobcapture/backend/app/routers/applications.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services import company_matcher

router = APIRouter(prefix="/api/applications", tags=["applications"])


class CompanyMatch(BaseModel):
    method: str
    summary_file: str
    jd_file: str | None = None
    script_file: str


class QuestionItem(BaseModel):
    id: str
    text: str
    field_selector: str
    char_limit: int | None = None
    word_limit: int | None = None
    field_type: str


class QuestionsPayload(BaseModel):
    company: str
    role: str
    application_url: str
    company_match: CompanyMatch
    questions: list[QuestionItem]


def _slug_has_outputs(slug: str) -> bool:
    summary = settings.output_summaries_dir / f"{slug}.yaml"
    script = settings.output_scripts_dir / f"generate_{slug}_resume.js"
    return summary.exists() and script.exists()


@router.post("/{company_slug}/questions", status_code=201)
def post_questions(company_slug: str, payload: QuestionsPayload) -> dict:
    if not _slug_has_outputs(company_slug):
        raise HTTPException(status_code=404, detail=f"No tailored outputs for slug '{company_slug}'")

    apps_dir: Path = settings.output_applications_dir
    apps_dir.mkdir(parents=True, exist_ok=True)

    record = payload.model_dump()
    record["captured_at"] = datetime.now(timezone.utc).isoformat()

    target = apps_dir / f"{company_slug}_questions.json"
    target.write_text(json.dumps(record, indent=2))
    return {"slug": company_slug, "path": str(target)}


@router.get("/pending")
def list_pending() -> list[dict]:
    apps_dir: Path = settings.output_applications_dir
    if not apps_dir.exists():
        return []
    pending: list[dict] = []
    for q in sorted(apps_dir.glob("*_questions.json")):
        slug = q.name.removesuffix("_questions.json")
        answers = apps_dir / f"{slug}_answers.json"
        if answers.exists():
            continue
        pending.append({"slug": slug, "questions_file": str(q)})
    return pending


@router.get("/match")
def match_company(company: str) -> dict:
    candidates = company_matcher.find_candidates(company)
    if len(candidates) == 1:
        return {"method": "auto", "candidates": candidates}
    if len(candidates) > 1:
        return {"method": "ambiguous", "candidates": candidates}
    return {"method": "none", "candidates": []}


@router.get("/{company_slug}/answers")
def get_answers(company_slug: str) -> dict:
    path = settings.output_applications_dir / f"{company_slug}_answers.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No answers for slug '{company_slug}'")
    return json.loads(path.read_text())
```

- [ ] **Step 2: Wire the router into `main.py`**

Modify `jobcapture/backend/app/main.py`:
- Add `applications` to the import line: `from app.routers import jobs, batches, export, history, applications`
- Add `app.include_router(applications.router)` after `app.include_router(history.router)`.

- [ ] **Step 3: Run the tests**

Run: `cd jobcapture/backend && pytest tests/test_applications.py -v`
Expected: PASS (7 tests).

- [ ] **Step 4: Run the full test suite to check no regressions**

Run: `cd jobcapture/backend && pytest -v`
Expected: All tests pass (including pre-existing jobs/batches/export/history/team_detector tests).

- [ ] **Step 5: Commit**

```bash
git add jobcapture/backend/app/routers/applications.py jobcapture/backend/app/main.py
git commit -m "feat(applications): add file-relay endpoints for question/answer flow"
```

---

## Task 7: Extension — question detection helpers

**Files:**
- Create: `jobcapture/extension/questions.js`

- [ ] **Step 1: Write the helpers**

Create `jobcapture/extension/questions.js`:

```javascript
(function () {
  // Shared helpers for question detection + answer auto-fill. Exposed on
  // window.JC_QUESTIONS so content.js can consume them without coupling.

  const NON_QUESTION_LABEL_REGEX =
    /^(first\s*name|last\s*name|full\s*name|preferred\s*name|email|phone|mobile|address|city|state|zip|postal|country|linkedin|github|website|portfolio|resume|cv|cover\s*letter|how\s+did\s+you\s+hear|referral|salary|current\s+company|current\s+title|date|availability)$/i;

  function visibleText(el) {
    if (!el) return "";
    return (el.innerText || el.textContent || "").trim();
  }

  function nearestLabelText(field) {
    // 1. Explicit <label for="id">
    if (field.id) {
      const lbl = document.querySelector(`label[for="${CSS.escape(field.id)}"]`);
      if (lbl) return visibleText(lbl);
    }
    // 2. Parent <label>
    const parentLabel = field.closest("label");
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true);
      // Strip the field itself from the clone so we get only the surrounding text.
      clone.querySelectorAll("input, textarea, select").forEach((n) => n.remove());
      const t = visibleText(clone);
      if (t) return t;
    }
    // 3. aria-labelledby
    const labelledBy = field.getAttribute("aria-labelledby");
    if (labelledBy) {
      const lbl = document.getElementById(labelledBy);
      if (lbl) return visibleText(lbl);
    }
    // 4. aria-label
    if (field.getAttribute("aria-label")) return field.getAttribute("aria-label").trim();
    // 5. Preceding heading or <div class*="label"> within the same form-group
    const container = field.closest("fieldset, .form-group, .field, [class*='question'], [class*='Question'], [class*='form-row']");
    if (container) {
      const heading = container.querySelector("label, legend, [class*='label'], [class*='Label'], [class*='question-title']");
      if (heading && heading !== field) {
        const t = visibleText(heading);
        if (t) return t;
      }
    }
    // 6. Previous sibling text
    let prev = field.previousElementSibling;
    for (let i = 0; i < 3 && prev; i++) {
      const t = visibleText(prev);
      if (t && t.length < 300) return t;
      prev = prev.previousElementSibling;
    }
    return "";
  }

  function extractLimits(field, labelText) {
    const maxlen = field.getAttribute("maxlength");
    const char_limit = maxlen ? parseInt(maxlen, 10) : null;

    let word_limit = null;
    // Look for "500 words", "Max 300 words", etc. in label + neighboring text
    const container = field.closest("fieldset, .form-group, .field, [class*='question'], div") || field.parentElement;
    const searchText = [labelText, container ? visibleText(container) : ""].join(" ");
    const m = searchText.match(/(?:max(?:imum)?\s+|up\s+to\s+|limit(?:ed)?\s+to\s+)?(\d{2,4})\s*words?/i);
    if (m) word_limit = parseInt(m[1], 10);
    return { char_limit, word_limit };
  }

  function looksLikeQuestion(labelText, field) {
    if (!labelText || labelText.length < 4) return false;
    if (NON_QUESTION_LABEL_REGEX.test(labelText.trim())) return false;
    if (field.type === "hidden" || field.disabled || field.readOnly) return false;
    // Require a free-text intent: textarea, OR input[type=text] with a long/instructional label
    const tag = field.tagName.toLowerCase();
    if (tag === "textarea") return true;
    if (tag === "input" && (field.type === "text" || field.type === "" || !field.type)) {
      // Short single-line inputs that look like questions (end with ?, contain phrases like "describe", "why", "what")
      return /\?\s*$/.test(labelText) || /\b(describe|why|what|how|tell\s+us|explain|share)\b/i.test(labelText);
    }
    return false;
  }

  function detect() {
    const fields = Array.from(document.querySelectorAll("textarea, input"));
    const questions = [];
    let counter = 0;
    for (const field of fields) {
      const label = nearestLabelText(field);
      if (!looksLikeQuestion(label, field)) continue;
      counter += 1;
      const { char_limit, word_limit } = extractLimits(field, label);
      const field_type = field.tagName.toLowerCase() === "textarea" ? "long_text" : "short_text";
      // Store both a stable selector and the raw text for fallback matching.
      let selector = "";
      if (field.id) selector = `#${CSS.escape(field.id)}`;
      else if (field.name) selector = `${field.tagName.toLowerCase()}[name="${CSS.escape(field.name)}"]`;
      else selector = `#__jc_q${counter}__`; // synthetic; we'll tag the element
      if (!field.id && !field.name) field.setAttribute("data-jc-question-id", `q${counter}`);
      questions.push({
        id: `q${counter}`,
        text: label,
        field_selector: selector,
        char_limit,
        word_limit,
        field_type,
      });
    }
    return questions;
  }

  function setFieldValue(field, value) {
    // Native setter + event dispatch so React/Vue/Angular pick up the change.
    const proto = field.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function flashField(field) {
    const prev = field.style.boxShadow;
    field.style.transition = "box-shadow 0.3s";
    field.style.boxShadow = "0 0 0 3px rgba(34, 197, 94, 0.7)";
    setTimeout(() => { field.style.boxShadow = prev; }, 900);
  }

  function locateField(answer) {
    // Try stored selector
    if (answer.field_selector) {
      try {
        const el = document.querySelector(answer.field_selector);
        if (el) return el;
      } catch (e) { /* invalid selector, keep trying */ }
    }
    // Synthetic selectors we set on detect()
    if (answer.id) {
      const el = document.querySelector(`[data-jc-question-id="${answer.id}"]`);
      if (el) return el;
    }
    // Fallback: match by label text
    if (answer.question_text) {
      const fields = Array.from(document.querySelectorAll("textarea, input"));
      for (const f of fields) {
        const label = nearestLabelText(f);
        if (label && label.trim() === answer.question_text.trim()) return f;
      }
    }
    return null;
  }

  function fill(answers) {
    const filled = [];
    const unmatched = [];
    for (const ans of answers) {
      const field = locateField(ans);
      if (!field) { unmatched.push(ans); continue; }
      if ((field.value || "").trim().length > 0) {
        // Never overwrite existing content — treat as unmatched for manual handling.
        unmatched.push({ ...ans, reason: "field_already_filled" });
        continue;
      }
      setFieldValue(field, ans.answer);
      flashField(field);
      filled.push(ans);
    }
    return { filled, unmatched };
  }

  window.JC_QUESTIONS = { detect, fill, nearestLabelText };
})();
```

- [ ] **Step 2: Manually sanity-check the syntax**

Run: `node -c jobcapture/extension/questions.js`
Expected: Exit code 0, no output (syntax OK).

- [ ] **Step 3: Commit**

```bash
git add jobcapture/extension/questions.js
git commit -m "feat(extension): add question detection and answer auto-fill helpers"
```

---

## Task 8: Update extension manifest

**Files:**
- Modify: `jobcapture/extension/manifest.json`

- [ ] **Step 1: Register questions.js**

Open `jobcapture/extension/manifest.json`. Replace the `content_scripts` block:

```json
  "content_scripts": [
    {
      "matches": ["https://*/*", "http://*/*"],
      "js": ["config.js", "questions.js", "content.js"],
      "run_at": "document_idle"
    }
  ],
```

Also bump the `version` field to `"0.4.0"` to signal the new capability.

- [ ] **Step 2: Verify the JSON parses**

Run: `python3 -c "import json; json.load(open('jobcapture/extension/manifest.json'))"`
Expected: No output (valid JSON).

- [ ] **Step 3: Commit**

```bash
git add jobcapture/extension/manifest.json
git commit -m "chore(extension): load questions.js before content.js"
```

---

## Task 9: Extension panel — question capture + answer fill UI

**Files:**
- Modify: `jobcapture/extension/content.js`

The existing panel in `content.js` has three sections (Detected / Batch / Footer). We add a fourth section ("Application Questions") that is shown only when `window.JC_QUESTIONS.detect()` returns ≥1 question.

- [ ] **Step 1: Append styles for the new section**

In `content.js`, locate the `STYLES` template literal (starts at line ~403). Append the following rules inside the backticks, after the existing `.jc-footer-btn:disabled` rule:

```css
    .jc-q-section { padding: 12px 16px; border-top: 1px solid rgba(0,0,0,0.05); }
    .jc-q-title { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
    .jc-q-subtle { font-size: 11px; color: #64748b; margin-bottom: 8px; }
    .jc-q-btn {
      width: 100%; padding: 9px; border: none; border-radius: 10px; cursor: pointer;
      font-size: 13px; font-weight: 600; margin-top: 6px;
      color: #ffffff;
      background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%);
      box-shadow: 0 2px 8px rgba(99,102,241,0.25);
      transition: all 0.15s ease;
    }
    .jc-q-btn:hover:not(:disabled) { transform: translateY(-0.5px); box-shadow: 0 4px 14px rgba(99,102,241,0.35); }
    .jc-q-btn:disabled { opacity: 0.5; cursor: default; }
    .jc-q-btn.secondary { background: rgba(241,245,249,0.9); color: #334155; box-shadow: none; border: 1px solid rgba(0,0,0,0.06); }
    .jc-q-preview { max-height: 180px; overflow-y: auto; margin-top: 8px; }
    .jc-q-item { padding: 8px; background: rgba(248,250,252,0.9); border-radius: 8px; margin-bottom: 6px; border: 1px solid rgba(0,0,0,0.04); }
    .jc-q-item-label { font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px; }
    .jc-q-item textarea { width: 100%; min-height: 60px; padding: 6px; border: 1px solid rgba(0,0,0,0.08); border-radius: 6px; font-size: 12px; font-family: inherit; resize: vertical; box-sizing: border-box; }
    .jc-q-dropdown { width: 100%; padding: 8px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.08); font-size: 13px; margin-top: 6px; }
    .jc-q-status { font-size: 12px; color: #475569; margin-top: 8px; }
    .jc-q-status.ok { color: #065f46; }
    .jc-q-status.warn { color: #92400e; }
```

- [ ] **Step 2: Insert the new panel section into the template**

In `content.js`, locate the widget `innerHTML` template (the backtick string assigned to `root.innerHTML`, line ~524). Insert the following block immediately after the closing `</div>` of the second `<div class="jc-divider"></div>` section — i.e., just before the `<div class="jc-footer">` line:

```html
      <div class="jc-q-section" id="jcQSection" style="display:none;">
        <div class="jc-q-title" id="jcQTitle">Application Questions</div>
        <div class="jc-q-subtle" id="jcQSubtle">—</div>
        <select class="jc-q-dropdown" id="jcQCompany" style="display:none;"></select>
        <button class="jc-q-btn" id="jcQCapture" disabled>Answer Questions</button>
        <button class="jc-q-btn secondary" id="jcQFill" style="display:none;">Fill Answers</button>
        <div class="jc-q-preview" id="jcQPreview"></div>
        <div class="jc-q-status" id="jcQStatus"></div>
      </div>
```

- [ ] **Step 3: Add the question-flow logic**

In `content.js`, locate the final closing `})();` of the IIFE. Immediately before it, append the following block:

```javascript
  // ── Application Questions Flow ───────────────────────────────
  // State:
  //   detectedQuestions: [{ id, text, field_selector, char_limit, word_limit, field_type }]
  //   activeSlug: string — the chosen output slug for this company
  //   answers: [{ id, field_selector, answer, char_count, within_limit }]

  let detectedQuestions = [];
  let activeSlug = null;
  let latestAnswers = null;
  let answersPollTimer = null;

  const qSection = document.getElementById("jcQSection");
  const qTitle = document.getElementById("jcQTitle");
  const qSubtle = document.getElementById("jcQSubtle");
  const qDropdown = document.getElementById("jcQCompany");
  const qCaptureBtn = document.getElementById("jcQCapture");
  const qFillBtn = document.getElementById("jcQFill");
  const qPreview = document.getElementById("jcQPreview");
  const qStatus = document.getElementById("jcQStatus");

  function setQStatus(msg, variant) {
    qStatus.textContent = msg || "";
    qStatus.classList.remove("ok", "warn");
    if (variant === "ok") qStatus.classList.add("ok");
    if (variant === "warn") qStatus.classList.add("warn");
  }

  async function initQuestionFlow() {
    if (!window.JC_QUESTIONS) return;
    detectedQuestions = window.JC_QUESTIONS.detect();
    if (detectedQuestions.length === 0) {
      qSection.style.display = "none";
      return;
    }
    qSection.style.display = "block";
    qSubtle.textContent = `${detectedQuestions.length} question${detectedQuestions.length > 1 ? "s" : ""} detected on this page`;

    // Resolve company from the current detection (currentJobData may be null on apply pages).
    const probeData = currentJobData || extractJobData();
    const companyName = probeData && probeData.company;
    if (!companyName) {
      setQStatus("Could not detect company on this page.", "warn");
      qCaptureBtn.disabled = true;
      return;
    }

    let matchBody;
    try {
      const resp = await fetch(`${API}/api/applications/match?company=${encodeURIComponent(companyName)}`);
      matchBody = await resp.json();
    } catch (e) {
      setQStatus("Backend unreachable.", "warn");
      return;
    }

    if (matchBody.method === "none" || matchBody.candidates.length === 0) {
      qCaptureBtn.disabled = true;
      qDropdown.style.display = "none";
      setQStatus(`No tailored resume for ${companyName}.`, "warn");
      return;
    }

    if (matchBody.candidates.length === 1) {
      activeSlug = matchBody.candidates[0].slug;
      qDropdown.style.display = "none";
      setQStatus(`Matched to ${activeSlug}.`, "ok");
    } else {
      qDropdown.style.display = "block";
      qDropdown.innerHTML = matchBody.candidates
        .map((c) => `<option value="${c.slug}">${c.slug}</option>`)
        .join("");
      activeSlug = matchBody.candidates[0].slug;
      qDropdown.addEventListener("change", () => {
        activeSlug = qDropdown.value;
        checkForAnswers();
      });
      setQStatus(`Multiple matches — confirm which applies.`, "warn");
    }

    qCaptureBtn.disabled = false;
    checkForAnswers();
  }

  async function checkForAnswers() {
    if (!activeSlug) return;
    clearTimeout(answersPollTimer);
    try {
      const resp = await fetch(`${API}/api/applications/${encodeURIComponent(activeSlug)}/answers`);
      if (resp.status === 404) {
        qFillBtn.style.display = "none";
        qPreview.innerHTML = "";
        return;
      }
      if (!resp.ok) return;
      latestAnswers = await resp.json();
      renderAnswerPreview();
    } catch (e) { /* backend offline — ignore */ }
  }

  function renderAnswerPreview() {
    if (!latestAnswers || !latestAnswers.answers) return;
    qFillBtn.style.display = "block";
    qPreview.innerHTML = latestAnswers.answers
      .map((a, idx) => `
        <div class="jc-q-item">
          <div class="jc-q-item-label">${(a.question_text || "Question " + (idx + 1)).slice(0, 140)}</div>
          <textarea data-ans-idx="${idx}">${a.answer || ""}</textarea>
        </div>`)
      .join("");
    qPreview.querySelectorAll("textarea").forEach((t) => {
      t.addEventListener("input", () => {
        latestAnswers.answers[parseInt(t.dataset.ansIdx, 10)].answer = t.value;
      });
    });
    setQStatus(`${latestAnswers.answers.length} answers ready to fill.`, "ok");
  }

  qCaptureBtn.addEventListener("click", async () => {
    if (!activeSlug || detectedQuestions.length === 0) return;
    qCaptureBtn.disabled = true;
    qCaptureBtn.textContent = "Sending…";
    const match = { method: "auto", summary_file: "", jd_file: "", script_file: "" };
    // Attach questions with the question text so the skill can reference it.
    const payload = {
      company: (currentJobData && currentJobData.company) || activeSlug,
      role: (currentJobData && currentJobData.title) || "",
      application_url: window.location.href,
      company_match: match,
      questions: detectedQuestions,
    };
    try {
      const resp = await fetch(`${API}/api/applications/${encodeURIComponent(activeSlug)}/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(await resp.text());
      qCaptureBtn.textContent = "Captured ✓";
      setQStatus("Run /answer-questions in Claude Code. Polling for answers…", "ok");
      // Poll every 5s for up to 5 minutes, stopping once answers appear.
      let tries = 0;
      const poll = async () => {
        tries += 1;
        await checkForAnswers();
        if (!latestAnswers && tries < 60) {
          answersPollTimer = setTimeout(poll, 5000);
        }
      };
      poll();
    } catch (e) {
      qCaptureBtn.textContent = "Error — retry";
      qCaptureBtn.disabled = false;
      setQStatus(String(e), "warn");
    }
  });

  qFillBtn.addEventListener("click", () => {
    if (!latestAnswers || !window.JC_QUESTIONS) return;
    // Re-map answer objects with question_text (from detected questions) for fallback matching.
    const enriched = latestAnswers.answers.map((a) => {
      const q = detectedQuestions.find((dq) => dq.id === a.id);
      return { ...a, question_text: q ? q.text : null };
    });
    const { filled, unmatched } = window.JC_QUESTIONS.fill(enriched);
    if (unmatched.length === 0) {
      setQStatus(`Filled ${filled.length} fields ✓`, "ok");
    } else {
      setQStatus(`Filled ${filled.length}; ${unmatched.length} need manual paste.`, "warn");
      // Show unmatched answers inline for copy-paste.
      const items = unmatched.map((u) => `<div class="jc-q-item"><div class="jc-q-item-label">${u.question_text || u.id}</div><textarea readonly>${u.answer}</textarea></div>`);
      qPreview.innerHTML = items.join("");
    }
  });

  // Trigger the flow whenever the panel opens.
  root.addEventListener("mouseenter", () => { setTimeout(initQuestionFlow, 200); });
  fab.addEventListener("click", () => { setTimeout(initQuestionFlow, 200); });
```

- [ ] **Step 4: Sanity-check JS syntax**

Run: `node -c jobcapture/extension/content.js`
Expected: Exit code 0.

- [ ] **Step 5: Commit**

```bash
git add jobcapture/extension/content.js
git commit -m "feat(extension): add application-question capture and fill panel"
```

---

## Task 10: Claude Code skill — answer-questions

**Files:**
- Create: `answer-questions/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `answer-questions/SKILL.md`:

````markdown
---
name: answer_questions_v1
description: "Generates answers to free-text application questions captured by the jobcapture extension. Reads the candidate's tailored resume outputs (summary, JD, resume script, career ledger) and the relevant prompt strategy, then writes structured answers for auto-fill and a human-readable markdown record. Trigger phrases: '/answer-questions', 'answer application questions', 'fill my application questions'."
---

# Answer Application Questions

## When to use
Invoke this skill when the jobcapture extension has captured application questions and written `output/applications/{slug}_questions.json`. The skill reads that file, generates answers using the company's existing tailored resume context, and writes `output/applications/{slug}_answers.json` + `{slug}_answers.md`.

## Pre-flight

1. **Scan for pending questions files.** List `output/applications/*_questions.json` whose companion `*_answers.json` does not exist.
2. **If exactly one pending file exists**, select it automatically.
3. **If multiple**, ask the user which slug to answer.
4. **If none**, stop and tell the user to capture questions from the extension first.

## Context loading

For the chosen slug, read — in this order:

1. `output/applications/{slug}_questions.json` — what to answer
2. `output/summaries/{slug}.yaml` — the content decisions made during tailoring (fit score, keywords placed, brief summary)
3. `output/jds/{slug}.txt` — the original job description (if present; not all slugs have one)
4. `output/scripts/generate_{slug}_resume.js` — the actual bullets on the submitted resume
5. `career_ledger.yaml` — the full experience bank for depth beyond the resume
6. `prompts/answer_strategies/default.yaml` — generation rules (tone, structure, length)

If any file in 1–2 or 4 is missing, stop and report the missing file. Items 3 and 5 are nice-to-have — warn but continue.

## Generation rules (from the strategy)

Follow the loaded strategy verbatim. The default strategy specifies:

- **Tone:** Confident but not arrogant. First-person. No filler.
- **Structure:** Lead with the direct answer, then support with specific examples.
- **Source priority:** submitted resume → JD keywords → career ledger. Never fabricate metrics not in the ledger.
- **Mirror JD terminology.** Don't swap in generic synonyms.
- **Don't contradict the resume.** If the resume already covers it, expand.
- **Length:**
  - With a `char_limit`: stay under 90% of the limit.
  - With a `word_limit`: stay under 90% of the limit.
  - No limit + `short_text`: 2–3 sentences.
  - No limit + `long_text`: 3–4 paragraphs with concrete examples.

For each question, before writing the answer:
1. Identify which resume bullet (or ledger achievement) is the primary evidence.
2. Extract 2–3 JD keywords the answer should mirror.
3. Draft, then verify the length rule. Trim if over.

## Output

Write two files:

**`output/applications/{slug}_answers.json`** — structured, for auto-fill:

```json
{
  "company": "...",
  "generated_at": "<ISO-8601 UTC>",
  "strategy_used": "default",
  "answers": [
    {
      "id": "q1",
      "field_selector": "...",
      "question_text": "...",
      "answer": "...",
      "char_count": 1234,
      "word_count": 210,
      "within_limit": true
    }
  ]
}
```

Copy each question's `id`, `field_selector`, and `text` (into `question_text`) from the input file so auto-fill can match on either selector or label text. Compute `char_count` and `word_count` from the answer body. `within_limit` is `true` when the answer respects the applicable limit.

**`output/applications/{slug}_answers.md`** — human-readable record. Use this format:

```markdown
# {Company} — {Role} Application

## {Question text}

{Answer body, with markdown paragraphs/headings if helpful}

## {Next question text}

{Next answer}
```

Match the format of existing files in `output/applications/` (e.g., `glia_sales_engineer.md`).

## Completion

Report to the user:
- The slug answered
- How many questions were answered
- Any questions whose answers came close to the length limit (flag within 5%)
- The two output file paths

Remind the user to return to the browser and click **Fill Answers** in the extension.
````

- [ ] **Step 2: Sanity check — the skill file exists and parses**

Run: `head -3 answer-questions/SKILL.md`
Expected: Prints the YAML frontmatter.

- [ ] **Step 3: Commit**

```bash
git add answer-questions/SKILL.md
git commit -m "feat(skill): add answer-questions skill for application free-text questions"
```

---

## Task 11: End-to-end manual verification

No automated test covers the full flow (extension ↔ backend ↔ skill), so verify by hand.

- [ ] **Step 1: Start the backend**

Run: `cd jobcapture/backend && uvicorn app.main:app --reload --port 8001`
Expected: Server starts; `/api/applications/pending` returns `[]` when `output/applications/` has no `*_questions.json` without a companion `*_answers.json`.

Verify in another terminal:
```bash
curl -s http://localhost:8001/api/applications/match?company=Glia | python3 -m json.tool
```
Expected: `{"method": "auto", "candidates": [{"slug": "glia", ...}]}` (assuming `output/summaries/glia.yaml` + script exist).

- [ ] **Step 2: Reload the Chrome extension**

In `chrome://extensions/`:
1. Toggle Developer Mode on.
2. Click **Reload** on JobCapture.
3. Confirm the version now reads `0.4.0`.

- [ ] **Step 3: Test question detection on a real apply form**

Visit a real application form page for a company that already has tailored outputs (e.g., open Glia's Sales Engineer apply page on Lever/Greenhouse).
Click the floating JobCapture widget (bottom-right).

Expected: The panel shows a new "Application Questions" section listing N questions. An "Answer Questions" button is enabled.

Click **Answer Questions**. Expected:
- Button changes to "Captured ✓"
- Status reads "Run /answer-questions in Claude Code. Polling for answers…"
- File appears at `output/applications/glia_questions.json` with the question list.

- [ ] **Step 4: Run `/answer-questions` in Claude Code**

Run the skill. Expected:
- It finds the pending file, loads all context, generates answers, writes `glia_answers.json` + `glia_answers.md`.
- Reports the output paths and any near-limit warnings.

- [ ] **Step 5: Fill answers**

Return to the browser. Panel should now show "Fill Answers" with previews.
Click **Fill Answers**. Expected: Each form field gets its answer; a green highlight flash appears on each field; status reads "Filled N fields ✓".

- [ ] **Step 6: Clean up the artifact files used for testing**

The test artifacts (`*_questions.json`, `*_answers.json`, `*_answers.md` for the test company) are fine to keep if you actually intend to submit. Otherwise remove them:

```bash
rm output/applications/<test_slug>_questions.json output/applications/<test_slug>_answers.json output/applications/<test_slug>_answers.md
```

- [ ] **Step 7: No commit needed**

If the manual flow exposed bugs, fix them in a new commit with `fix(...)` scope and rerun this task.

---

## Out of Scope (deferred)

- Multiple choice / dropdown / checkbox questions (spec: "Out of Scope")
- Strategy auto-classification per question (spec: "Extensibility"); a future task can add `prompts/answer_strategies/why_this_company.yaml` and a classifier, but the default strategy is sufficient for MVP.
- UI-level tests for the extension (no existing JS test harness; follow the project's manual-verification convention).
