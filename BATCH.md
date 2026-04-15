---
name: batch_resume_tailoring
description: "Batch-processes multiple job descriptions from an Excel file, dispatching parallel sub-agents to tailor a resume for each JD using the existing SKILL.md pipeline. Trigger phrases: 'batch tailor', 'batch tailor auto', 'batch tailor manual', 'run batch', 'process all JDs', or when user provides an Excel file with company names and JD texts."
---

# Batch Resume Tailoring

Orchestrates parallel resume tailoring for multiple JDs from a single Excel input.

## Input File Selection

The batch tool supports three input sources:

| Trigger | Input File | Source |
|---------|-----------|--------|
| `batch tailor` | `inputs/batch_jds.xlsx` | Default (backward compatible) |
| `batch tailor auto` | `inputs/batch_jds_auto.xlsx` | JobScan automated scanner |
| `batch tailor manual` | `inputs/batch_jds_manual.xlsx` | JobCapture browser extension |

All three files use the same format: Column A = Company Name, Column B = Job Description text. Extra columns (url, location) are ignored by the parser.

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

Determine which input file to use based on the trigger phrase:
- If triggered with `batch tailor auto`: use `inputs/batch_jds_auto.xlsx`
- If triggered with `batch tailor manual`: use `inputs/batch_jds_manual.xlsx`
- Otherwise: use `inputs/batch_jds.xlsx`

```bash
python3 scripts/batch_read_excel.py <selected_input_file>
```

Capture the JSON array from stdout. Each entry has: `company`, `slug`, `row_index`, `jd_text`.

The script also writes `output/summaries/manifest.json` (used later by the merge script).

Validate: JSON should be a non-empty array. Report the count to the user:
"Found N job descriptions. Dispatching N parallel agents."

## Step 2: Dispatch Parallel Sub-Agents

For EACH entry in the JSON array, dispatch a sub-agent using the Agent tool.
**Dispatch ALL sub-agents in a single message** (parallel execution).

Use this prompt template per sub-agent (replace `{placeholders}`):

~~~
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
  output/keywords/jd_keywords_{slug}.yaml, gap resolution, fit assessment.
- Run Phase 2 fully: shortlist (with reframing gate), select, write bullets
  (with JD verb mirroring), summary + skills (3-criteria filter), full audit.
- Run Phase 3 fully: generate script saved as output/scripts/generate_{slug}_resume.js,
  build .docx, convert to PDF, PDF verification using the SKILL.md two-stage
  gate (Stage 1: target ≥66 lines; Stage 2: enforce 1 page). If underfilled,
  follow `references/add_bullet.md`, regenerate, and re-check until the resume
  passes or no truthful expansion remains.
- After completion, write a summary YAML to output/summaries/{slug}.yaml with
  fields: company, role_title, slug, fit_score, keywords_placed, keywords_total,
  keywords_missing (list), output_docx, output_pdf, pages, lines, brief_summary
  (3-5 sentences), status ("SUCCESS").
- If you encounter an unrecoverable error, write a summary YAML with
  status: "FAILED" and an error field describing what went wrong.
~~~

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
