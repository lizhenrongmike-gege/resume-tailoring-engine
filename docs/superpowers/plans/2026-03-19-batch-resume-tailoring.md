# Batch Resume Tailoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a modular batch orchestration layer that processes N job descriptions from an Excel file in parallel, producing one tailored resume per JD — without modifying any existing files.

**Architecture:** Two Python utility scripts handle Excel I/O (read and merge). A BATCH.md instruction file tells the orchestrating agent how to parse, dispatch parallel sub-agents, and collect results. Each sub-agent independently reads the existing SKILL.md and runs the full tailoring pipeline.

**Tech Stack:** Python 3 (openpyxl, pyyaml), existing Node.js resume pipeline (unchanged)

**Spec:** `docs/superpowers/specs/2026-03-19-batch-resume-tailoring-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/batch_read_excel.py` | Create | Read Excel → JSON stdout + manifest.json |
| `scripts/batch_merge_summaries.py` | Create | Read summary YAMLs → write results Excel |
| `BATCH.md` | Create | Orchestration instructions for the agent |
| `tests/test_batch_read.py` | Create | Verify Excel parsing, slug derivation, collision handling |
| `tests/test_batch_merge.py` | Create | Verify summary merging, failure handling, backup behavior |
| `tests/fixtures/sample_batch.xlsx` | Create | 3-row test Excel for script testing |

**Existing files: NO modifications.** SKILL.md, career_ledger.yaml, scripts/resume_template.js, etc. remain untouched.

---

### Task 1: Install Dependencies and Create Test Fixture

**Files:**
- Create: `tests/fixtures/sample_batch.xlsx`
- Create: `tests/create_fixture.py` (one-time helper to generate the test Excel)

- [ ] **Step 1: Install openpyxl and pyyaml**

```bash
pip install openpyxl pyyaml
```

Expected: both install successfully.

- [ ] **Step 2: Create the test fixture generator**

Create `tests/create_fixture.py`:

```python
#!/usr/bin/env python3
"""One-time script to create the test Excel fixture."""
import os
from openpyxl import Workbook

os.makedirs("tests/fixtures", exist_ok=True)
wb = Workbook()
ws = wb.active
ws.append(["Company Name", "Job Description", "Summary"])
ws.append(["TestCorp", "We need a Data Analyst with SQL, Python, and Tableau experience. 2+ years required.", ""])
ws.append(["TestCorp", "Looking for a Risk Analyst with strong SQL and Excel skills.", ""])
ws.append(["Acme Inc", "Hiring a Business Intelligence Analyst. Must know BigQuery, Looker, and dbt.", ""])
wb.save("tests/fixtures/sample_batch.xlsx")
print("Created tests/fixtures/sample_batch.xlsx")
```

Note: Two "TestCorp" rows intentionally test slug collision handling.

- [ ] **Step 3: Run the fixture generator**

```bash
python3 tests/create_fixture.py
```

Expected: `tests/fixtures/sample_batch.xlsx` created with 3 data rows + 1 header.

- [ ] **Step 4: Verify the fixture**

```bash
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('tests/fixtures/sample_batch.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(row)
"
```

Expected: 4 rows printed (1 header + 3 data).

- [ ] **Step 5: Commit**

```bash
git add tests/create_fixture.py tests/fixtures/sample_batch.xlsx
git commit -m "chore: add test fixture for batch resume tailoring"
```

---

### Task 2: Write batch_read_excel.py

**Files:**
- Create: `scripts/batch_read_excel.py`
- Test: `tests/test_batch_read.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_batch_read.py`:

```python
#!/usr/bin/env python3
"""Tests for batch_read_excel.py."""
import json
import os
import subprocess
import sys

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


if __name__ == "__main__":
    tests = [
        test_basic_parsing,
        test_slug_derivation,
        test_slug_collision,
        test_manifest_written,
        test_entry_fields,
        test_file_not_found,
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/test_batch_read.py
```

Expected: FAIL (script doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `scripts/batch_read_excel.py`:

```python
#!/usr/bin/env python3
"""Read a batch JD Excel file and output structured JSON.

Usage: python3 scripts/batch_read_excel.py <path_to_xlsx>

Input:  Excel with Column A = Company Name, Column B = JD text (header in row 1)
Output: JSON array to stdout: [{company, slug, row_index, jd_text}, ...]
Side effect: writes output/summaries/manifest.json mapping row_index → slug
"""
import json
import os
import re
import sys

from openpyxl import load_workbook


def derive_slug(company_name):
    """Lowercase, replace non-alphanumeric with underscores, strip edges."""
    slug = company_name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def main():
    if len(sys.argv) < 2:
        print("Usage: batch_read_excel.py <path_to_xlsx>", file=sys.stderr)
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"Error: file not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    wb = load_workbook(xlsx_path)
    ws = wb.active

    entries = []
    slug_counts = {}

    for row in ws.iter_rows(min_row=2, values_only=False):
        company = row[0].value
        jd_text = row[1].value

        if not company or not jd_text:
            continue

        company = str(company).strip()
        jd_text = str(jd_text).strip()
        row_index = row[0].row

        base_slug = derive_slug(company)
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            slug = f"{base_slug}_{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 1
            slug = base_slug

        entries.append({
            "company": company,
            "slug": slug,
            "row_index": row_index,
            "jd_text": jd_text,
        })

    if not entries:
        print("Error: no data rows found in Excel", file=sys.stderr)
        sys.exit(1)

    # Write manifest
    os.makedirs("output/summaries", exist_ok=True)
    manifest = {str(e["row_index"]): e["slug"] for e in entries}
    with open("output/summaries/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Output JSON to stdout
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/test_batch_read.py
```

Expected: 6/6 tests passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/batch_read_excel.py tests/test_batch_read.py
git commit -m "feat: add batch_read_excel.py with slug collision handling"
```

---

### Task 3: Write batch_merge_summaries.py

**Files:**
- Create: `scripts/batch_merge_summaries.py`
- Test: `tests/test_batch_merge.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_batch_merge.py`:

```python
#!/usr/bin/env python3
"""Tests for batch_merge_summaries.py."""
import json
import os
import shutil
import subprocess
import sys

import yaml

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "batch_merge_summaries.py")
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_batch.xlsx")
SUMMARIES_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "summaries")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


def setup():
    """Create manifest and sample summary YAMLs."""
    os.makedirs(SUMMARIES_DIR, exist_ok=True)

    manifest = {"2": "testcorp", "3": "testcorp_2", "4": "acme_inc"}
    with open(os.path.join(SUMMARIES_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    success_summary = {
        "company": "TestCorp",
        "role_title": "Data Analyst",
        "slug": "testcorp",
        "fit_score": "80%",
        "keywords_placed": 10,
        "keywords_total": 12,
        "keywords_missing": ["BigQuery"],
        "output_docx": "output/doc/TestCorp_Data_Analyst_Resume.docx",
        "output_pdf": "output/pdf/TestCorp_Data_Analyst_Resume.pdf",
        "pages": 1,
        "lines": 55,
        "brief_summary": "Strong match. SQL and Python coverage excellent.",
        "status": "SUCCESS",
    }
    with open(os.path.join(SUMMARIES_DIR, "testcorp.yaml"), "w") as f:
        yaml.dump(success_summary, f)

    failed_summary = {
        "company": "TestCorp",
        "slug": "testcorp_2",
        "status": "FAILED",
        "error": "Sub-agent did not produce output",
    }
    with open(os.path.join(SUMMARIES_DIR, "testcorp_2.yaml"), "w") as f:
        yaml.dump(failed_summary, f)

    # acme_inc: no summary YAML (tests missing summary handling)


def run_script(xlsx_path):
    result = subprocess.run(
        [sys.executable, SCRIPT, xlsx_path],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    return result


def test_results_file_created():
    """Merge should create a _results.xlsx file."""
    result = run_script(FIXTURE)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    assert os.path.exists(results_path), "Results file not created"


def test_success_summary_written():
    """Column C of success row should contain brief_summary."""
    run_script(FIXTURE)
    from openpyxl import load_workbook
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    wb = load_workbook(results_path)
    ws = wb.active
    cell_c2 = ws.cell(row=2, column=3).value
    assert cell_c2 is not None, "Column C row 2 is empty"
    assert "Strong match" in cell_c2, f"Unexpected summary: {cell_c2}"


def test_failed_summary_written():
    """Column C of failed row should contain [FAILED] prefix."""
    run_script(FIXTURE)
    from openpyxl import load_workbook
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    wb = load_workbook(results_path)
    ws = wb.active
    cell_c3 = ws.cell(row=3, column=3).value
    assert cell_c3 is not None, "Column C row 3 is empty"
    assert "[FAILED]" in cell_c3, f"Expected [FAILED] prefix: {cell_c3}"


def test_missing_summary_handled():
    """Column C of missing summary row should contain [MISSING] prefix."""
    run_script(FIXTURE)
    from openpyxl import load_workbook
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    wb = load_workbook(results_path)
    ws = wb.active
    cell_c4 = ws.cell(row=4, column=3).value
    assert cell_c4 is not None, "Column C row 4 is empty"
    assert "[MISSING]" in cell_c4, f"Expected [MISSING] prefix: {cell_c4}"


def test_original_file_preserved():
    """Original Excel should not be modified."""
    from openpyxl import load_workbook
    wb = load_workbook(FIXTURE)
    ws = wb.active
    cell_c2 = ws.cell(row=2, column=3).value
    assert cell_c2 is None or cell_c2 == "", "Original file was modified"


def cleanup():
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    if os.path.exists(results_path):
        os.remove(results_path)
    for fname in ["manifest.json", "testcorp.yaml", "testcorp_2.yaml"]:
        fpath = os.path.join(SUMMARIES_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)


if __name__ == "__main__":
    setup()
    tests = [
        test_results_file_created,
        test_success_summary_written,
        test_failed_summary_written,
        test_missing_summary_handled,
        test_original_file_preserved,
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
    cleanup()
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/test_batch_merge.py
```

Expected: FAIL (script doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `scripts/batch_merge_summaries.py`:

```python
#!/usr/bin/env python3
"""Merge summary YAMLs back into the batch Excel file.

Usage: python3 scripts/batch_merge_summaries.py <path_to_xlsx>

Reads output/summaries/manifest.json for row→slug mapping.
Reads output/summaries/{slug}.yaml for each row's summary.
Writes results to {input_name}_results.xlsx (preserves original).
"""
import json
import os
import sys

import yaml
from openpyxl import load_workbook


def main():
    if len(sys.argv) < 2:
        print("Usage: batch_merge_summaries.py <path_to_xlsx>", file=sys.stderr)
        sys.exit(1)

    xlsx_path = sys.argv[1]
    manifest_path = "output/summaries/manifest.json"

    if not os.path.exists(xlsx_path):
        print(f"Error: file not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(manifest_path):
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    wb = load_workbook(xlsx_path)
    ws = wb.active

    for row_index_str, slug in manifest.items():
        row_idx = int(row_index_str)
        summary_path = f"output/summaries/{slug}.yaml"

        if not os.path.exists(summary_path):
            ws.cell(row=row_idx, column=3, value=f"[MISSING] No summary produced for {slug}")
            print(f"Warning: missing summary for {slug}", file=sys.stderr)
            continue

        with open(summary_path) as f:
            summary = yaml.safe_load(f)

        if summary.get("status") == "FAILED":
            error_msg = summary.get("error", "Unknown error")
            ws.cell(row=row_idx, column=3, value=f"[FAILED] {error_msg}")
        else:
            ws.cell(row=row_idx, column=3, value=summary.get("brief_summary", "No summary available"))

    # Write to _results.xlsx to preserve original
    base, ext = os.path.splitext(xlsx_path)
    output_path = f"{base}_results{ext}"
    wb.save(output_path)
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/test_batch_merge.py
```

Expected: 5/5 tests passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/batch_merge_summaries.py tests/test_batch_merge.py
git commit -m "feat: add batch_merge_summaries.py with failure and missing handling"
```

---

### Task 4: Write BATCH.md

**Files:**
- Create: `BATCH.md`

- [ ] **Step 1: Write BATCH.md**

Create `BATCH.md` with the following content:

```markdown
---
name: batch_resume_tailoring
description: "Batch-processes multiple job descriptions from an Excel file, dispatching parallel sub-agents to tailor a resume for each JD using the existing SKILL.md pipeline. Trigger phrases: 'batch tailor', 'run batch', 'process all JDs', or when user provides an Excel file with company names and JD texts."
---

# Batch Resume Tailoring

Orchestrates parallel resume tailoring for multiple JDs from a single Excel input.

## Prerequisites (run once before dispatching)

1. **Python deps:** `pip install openpyxl pyyaml`
2. **Verify `career_ledger.yaml`** exists in the project root.
3. **Verify SKILL.md dependencies** (run each, abort if any fail):
   ```bash
   node -e "require('docx'); console.log('docx OK')"
   which libreoffice && which pdfinfo && which pdftotext && which pandoc
   ```
   Note: `pdftotext` is from the same poppler package as `pdfinfo`.
4. **Create output directories:**
   ```bash
   mkdir -p output/summaries output/doc output/pdf
   ```

## Step 1: Parse the Excel

```bash
python3 scripts/batch_read_excel.py inputs/batch_jds.xlsx
```

Capture the JSON array from stdout. Each entry has: `company`, `slug`, `row_index`, `jd_text`.

The script also writes `output/summaries/manifest.json` (used later by the merge script).

Validate: JSON should be a non-empty array. Report the count to the user:
"Found N job descriptions. Dispatching N parallel agents."

## Step 2: Dispatch Parallel Sub-Agents

For EACH entry in the JSON array, dispatch a sub-agent using the Agent tool.
**Dispatch ALL sub-agents in a single message** (parallel execution).

Use this prompt template per sub-agent (replace `{placeholders}`):

```
You are tailoring a resume to a job description. Follow these steps exactly:

1. Read {absolute_path_to_SKILL.md} completely before starting. This is your
   instruction manual — follow every phase in order.
2. Career ledger: {absolute_path_to_career_ledger.yaml} (read-only source of truth).
3. Company: {company} | Slug: {slug}
4. Job Description:
{jd_text}

INSTRUCTIONS:
- Working directory: {absolute_path_to_project_root}
- Skip Phase 0a (dependencies pre-verified) and Phase 0b (ledger exists).
- Run Phase 1 fully: JD analysis, must-cover checklist saved to
  jd_keywords_{slug}.yaml, gap resolution, fit assessment.
- Run Phase 2 fully: shortlist (with reframing gate), select, write bullets
  (with JD verb mirroring), summary + skills (3-criteria filter), full audit.
- Run Phase 3 fully: generate script saved as generate_{slug}_resume.js,
  build .docx, convert to PDF, PDF verification using the SKILL.md underfill gate
  (`TARGET_FULL_LINES = 69`, `MIN_PASS_LINES = 66`). If underfilled, follow
  `references/add_bullet.md`, regenerate, and re-check until the resume passes
  or no truthful expansion remains.
- After completion, write a summary YAML to output/summaries/{slug}.yaml with
  fields: company, role_title, slug, fit_score, keywords_placed, keywords_total,
  keywords_missing (list), output_docx, output_pdf, pages, lines, brief_summary
  (3-5 sentences), status ("SUCCESS").
- If you encounter an unrecoverable error, write a summary YAML with
  status: "FAILED" and an error field describing what went wrong.
```

## Step 3: Monitor & Checkpoint

As each sub-agent completes:

1. Check if `output/summaries/{slug}.yaml` exists.
2. **If YES:** Read it and report a checkpoint to the user:
   `"{company} — {role_title} — {fit_score} — {status}"`
3. **If NO (crash fallback):** Write a FAILED summary YAML for that slug:
   ```yaml
   company: "{company}"
   slug: "{slug}"
   status: "FAILED"
   error: "Sub-agent did not produce output"
   ```
   Report: `"{company} — FAILED — sub-agent did not produce output"`

## Step 4: Merge Results & Final Report

After ALL sub-agents have completed:

```bash
python3 scripts/batch_merge_summaries.py inputs/batch_jds.xlsx
```

This writes `inputs/batch_jds_results.xlsx` with Column C populated.

Present a final summary table to the user:

| # | Company | Role | Fit | Keywords | Status | Gaps |
|---|---------|------|-----|----------|--------|------|
| 1 | ... | ... | ...% | X/Y | SUCCESS | ... |

Report the output file path and total SUCCESS/FAILED counts.
```

- [ ] **Step 2: Review BATCH.md for correctness**

Read through `BATCH.md` and verify:
- All file paths match the spec
- Prompt template matches spec exactly
- No SKILL.md logic leaked into BATCH.md
- Prerequisites cover all dependencies

- [ ] **Step 3: Commit**

```bash
git add BATCH.md
git commit -m "feat: add BATCH.md orchestration instructions for batch resume tailoring"
```

---

### Task 5: End-to-End Integration Test

**Purpose:** Verify the full pipeline works: Excel parse → dispatch → merge. This test uses the helper scripts only (not the full SKILL.md sub-agent pipeline, which would require actual LLM calls).

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_integration.py`:

```python
#!/usr/bin/env python3
"""Integration test: parse → simulate summaries → merge."""
import json
import os
import subprocess
import sys

import yaml

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
READ_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "batch_read_excel.py")
MERGE_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "batch_merge_summaries.py")
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_batch.xlsx")
SUMMARIES_DIR = os.path.join(PROJECT_ROOT, "output", "summaries")


def test_full_pipeline():
    """Parse Excel → simulate summary YAMLs → merge back to Excel."""

    # Step 1: Parse
    result = subprocess.run(
        [sys.executable, READ_SCRIPT, FIXTURE],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"Read script failed: {result.stderr}"
    entries = json.loads(result.stdout)
    assert len(entries) == 3

    # Step 2: Simulate sub-agent output (write summary YAMLs)
    for entry in entries:
        summary = {
            "company": entry["company"],
            "role_title": "Test Role",
            "slug": entry["slug"],
            "fit_score": "85%",
            "keywords_placed": 8,
            "keywords_total": 10,
            "keywords_missing": ["SomeSkill", "AnotherSkill"],
            "output_docx": f"output/doc/{entry['company']}_Test_Role_Resume.docx",
            "output_pdf": f"output/pdf/{entry['company']}_Test_Role_Resume.pdf",
            "pages": 1,
            "lines": 55,
            "brief_summary": f"Simulated summary for {entry['company']}. Good match.",
            "status": "SUCCESS",
        }
        with open(os.path.join(SUMMARIES_DIR, f"{entry['slug']}.yaml"), "w") as f:
            yaml.dump(summary, f)

    # Step 3: Merge
    result = subprocess.run(
        [sys.executable, MERGE_SCRIPT, FIXTURE],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, f"Merge script failed: {result.stderr}"

    # Step 4: Verify results Excel
    from openpyxl import load_workbook
    results_path = FIXTURE.replace(".xlsx", "_results.xlsx")
    assert os.path.exists(results_path), "Results file not created"

    wb = load_workbook(results_path)
    ws = wb.active

    for row_idx in [2, 3, 4]:
        cell = ws.cell(row=row_idx, column=3).value
        assert cell is not None, f"Row {row_idx} Column C is empty"
        assert "Simulated summary" in cell, f"Row {row_idx} unexpected: {cell}"

    print("PASS: Full pipeline integration test")

    # Cleanup
    os.remove(results_path)
    for entry in entries:
        yaml_path = os.path.join(SUMMARIES_DIR, f"{entry['slug']}.yaml")
        if os.path.exists(yaml_path):
            os.remove(yaml_path)


if __name__ == "__main__":
    try:
        test_full_pipeline()
        sys.exit(0)
    except (AssertionError, Exception) as e:
        print(f"FAIL: {e}")
        sys.exit(1)
```

- [ ] **Step 2: Run the integration test**

```bash
python3 tests/test_integration.py
```

Expected: `PASS: Full pipeline integration test`

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for batch pipeline"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run all tests together**

```bash
python3 tests/test_batch_read.py && python3 tests/test_batch_merge.py && python3 tests/test_integration.py
```

Expected: All tests pass.

- [ ] **Step 2: Verify no existing files were modified**

```bash
git diff HEAD -- SKILL.md career_ledger.yaml scripts/resume_template.js scripts/build_ledger.py
```

Expected: No output (no changes to existing files).

- [ ] **Step 3: Verify new file inventory matches spec**

New files should be exactly:
- `BATCH.md`
- `scripts/batch_read_excel.py`
- `scripts/batch_merge_summaries.py`
- `tests/create_fixture.py`
- `tests/fixtures/sample_batch.xlsx`
- `tests/test_batch_read.py`
- `tests/test_batch_merge.py`
- `tests/test_integration.py`

- [ ] **Step 4: Final commit if any loose changes**

```bash
git status
```
