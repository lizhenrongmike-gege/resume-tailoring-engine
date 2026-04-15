# Batch Resume Tailoring — Design Spec

## Problem

The resume tailoring skill (SKILL.md v6) produces high-quality, ATS-optimized resumes but requires a dedicated chat session per JD. Users applying to 10+ positions want to provide a batch of JDs and receive tailored resumes for all of them with minimal manual intervention.

## Goals

- Process N job descriptions in parallel from a single Excel input file.
- Produce the same quality output as a manual single-JD tailoring session.
- Keep the existing SKILL.md and all its scripts/references completely untouched.
- Provide a summary dashboard (in the Excel file) for easy review.

## Non-Goals

- URL scraping / auto-extraction from job sites (future add-on).
- Modifying SKILL.md or any existing pipeline logic.
- Cross-JD context sharing (each tailoring is independent).

---

## Architecture

### New Files (add-on only)

```
BATCH.md                        — orchestration instructions for the agent
scripts/batch_read_excel.py     — reads Excel → JSON to stdout
scripts/batch_merge_summaries.py — reads summary YAMLs → writes column C to Excel
```

### Existing Files (unchanged)

```
SKILL.md                        — single-JD tailoring pipeline (read by sub-agents)
career_ledger.yaml              — candidate experience (read by sub-agents)
scripts/resume_template.js      — formatting module (used by sub-agents)
scripts/build_ledger.py         — ledger initialization (not involved in batch)
```

### Dependencies

- `openpyxl` — Python library for Excel I/O. Install via `pip install openpyxl`.

---

## Input Format

File: `inputs/batch_jds.xlsx`

| Column A (Company Name) | Column B (Job Description) | Column C (Summary — auto-filled) |
|--------------------------|----------------------------|-----------------------------------|
| OneMagnify | Full JD text... | (populated after processing) |
| Dialpad | Full JD text... | (populated after processing) |

- Column A: Company name (used to derive the file slug).
- Column B: Full JD text pasted into the cell.
- Column C: Left empty by the user; populated by the merge script after processing.

**Slug derivation:** `batch_read_excel.py` derives the slug from the company name (lowercase, spaces/special chars → underscores). If two rows have the same company name (e.g., two Google positions), the script appends `_2`, `_3`, etc. to guarantee uniqueness. The script outputs the definitive slug per row — all downstream components (sub-agent prompts, merge script) use this slug, never re-derive it.

---

## Output Structure

### Per-JD Artifacts

Each sub-agent produces:

| Artifact | Path |
|----------|------|
| Generate script | `generate_{slug}_resume.js` |
| Keyword checklist | `jd_keywords_{slug}.yaml` |
| Word document | `output/doc/{Company}_{Role}_Resume.docx` |
| PDF | `output/pdf/{Company}_{Role}_Resume.pdf` |
| Summary | `output/summaries/{slug}.yaml` |

### Summary YAML Schema

```yaml
company: "OneMagnify"
role_title: "Data Analyst"
slug: "onemagnify"
fit_score: "75-80%"
keywords_placed: 10
keywords_total: 12
keywords_missing: ["Big Query", "Qlik Sense"]
output_docx: "output/doc/OneMagnify_Data_Analyst_Resume.docx"
output_pdf: "output/pdf/OneMagnify_Data_Analyst_Resume.pdf"
pages: 1
lines: 68
brief_summary: "Strong SQL/data wrangling match. 5 roles + 1 project, 14 bullets. Gaps: Big Query (SQL adjacent), Qlik Sense (Tableau adjacent)."
status: "SUCCESS"
```

On failure:

```yaml
company: "SomeCompany"
slug: "somecompany"
status: "FAILED"
error: "Description of what went wrong"
```

### Merged Excel Output

Written to `inputs/batch_jds_results.xlsx` (original input preserved as backup). Column C is populated with the `brief_summary` field from each summary YAML. Failed rows get the error message instead.

---

## Pipeline Flow

```
1. Agent reads BATCH.md
2. Agent runs: python3 scripts/batch_read_excel.py inputs/batch_jds.xlsx
   → JSON array to stdout: [{company, slug, row_index, jd_text}, ...]
   → Also writes output/summaries/manifest.json mapping row_index → slug
3. Agent verifies dependencies ONCE:
   - node -e "require('docx')"
   - which libreoffice, pdfinfo, pdftotext, pandoc
     (pdftotext is provided by the same poppler/poppler-utils package as pdfinfo)
   - python3 -c "import openpyxl"
   - career_ledger.yaml exists
   - mkdir -p output/summaries output/doc output/pdf
4. Agent dispatches N parallel sub-agents (one per JD)
   Working directory for each sub-agent: project root (where package.json,
   node_modules, and career_ledger.yaml live)
5. Each sub-agent:
   a. Reads SKILL.md completely
   b. Reads career_ledger.yaml
   c. Runs Phases 1-3 of SKILL.md for its assigned JD
   d. Writes summary YAML to output/summaries/{slug}.yaml
6. As each sub-agent completes, orchestrator reports checkpoint to user.
   CRASH FALLBACK: if a sub-agent returns without producing
   output/summaries/{slug}.yaml, the orchestrator writes a FAILED
   summary YAML for that slug with error: "Sub-agent did not produce output."
7. After all complete:
   python3 scripts/batch_merge_summaries.py inputs/batch_jds.xlsx
8. Agent presents final summary table to user
```

---

## Sub-Agent Prompt Template

```
You are tailoring a resume to a job description. Follow these steps exactly:

1. Read {skill_md_path} completely before starting. This is your instruction
   manual — follow every phase in order.
2. Career ledger: {ledger_path} (read-only source of truth).
3. Company: {company_name} | Slug: {slug}
4. Job Description:
   {jd_text}

INSTRUCTIONS:
- Skip Phase 0a (dependencies pre-verified) and Phase 0b (ledger exists).
- Run Phase 1 fully: JD analysis, must-cover checklist saved to
  jd_keywords_{slug}.yaml, gap resolution, fit assessment.
- Run Phase 2 fully: shortlist (with reframing gate), select, write bullets
  (with JD verb mirroring), summary + skills (3-criteria filter), full audit.
- Run Phase 3 fully: generate script saved as generate_{slug}_resume.js,
  build .docx, convert to PDF, PDF verification (must be 1 page, >=42 lines).
- After completion, write a summary YAML to output/summaries/{slug}.yaml with
  fields: company, role_title, slug, fit_score, keywords_placed, keywords_total,
  keywords_missing (list), output_docx, output_pdf, pages, lines, brief_summary
  (3-5 sentences), status ("SUCCESS").
- If you encounter an unrecoverable error, write a summary YAML with
  status: "FAILED" and an error field describing what went wrong.
```

---

## Quality Guardrails

No additional quality logic needed — SKILL.md v6 already enforces:

- Reframing gate before marking any role OUT (Step 2.1)
- JD verb mirroring in bullet writing (Step 2.3)
- 3-criteria include/exclude filter for skills section (Step 2.4)
- Full content audit with keyword verification (Step 2.5)
- PDF page count as source of truth (Phase 3 Step 4)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Fit < 60% | Sub-agent notes weak match in summary, still produces resume |
| PDF > 1 page | Sub-agent trims per SKILL.md rules, re-verifies |
| Sub-agent crashes | Orchestrator detects missing summary YAML and writes FAILED entry; other JDs unaffected |
| Excel parse error | Orchestrator reports error before dispatching, no sub-agents spawned |
| Missing dependencies | Orchestrator reports missing deps, aborts before dispatching |

---

## Scripts

### batch_read_excel.py

- Input: path to `.xlsx` file (CLI argument)
- Output: JSON array to stdout: `[{company, slug, row_index, jd_text}, ...]`
- Side effect: writes `output/summaries/manifest.json` mapping `row_index → slug` (used by merge script to avoid re-deriving slugs)
- Slug derivation: lowercase company name, spaces/special chars → underscores. On collision (duplicate company names), append `_2`, `_3`, etc. Example: two Google rows → `google`, `google_2`
- Logic: skip header row; read column A (company) and column B (JD text) for each non-empty row
- Validation: error if file not found, no data rows, or empty cells in A/B

### batch_merge_summaries.py

- Input: path to `.xlsx` file (CLI argument)
- Logic: read `output/summaries/manifest.json` to get the row → slug mapping (never re-derives slugs); for each row, read `output/summaries/{slug}.yaml`; extract `brief_summary` (or error message if status is FAILED); write to column C
- Output: writes to `inputs/batch_jds_results.xlsx` (preserves original input file as backup)
- Validation: warn (don't error) if a summary YAML is missing for a row

---

## BATCH.md Structure (~80 lines)

1. **Trigger** — when user says "batch tailor" or provides an Excel with JDs
2. **Prerequisites** — verify openpyxl, verify career_ledger.yaml, run Phase 0a checks once
3. **Parse** — run batch_read_excel.py, validate JSON output
4. **Dispatch** — sub-agent prompt template, dispatch all in parallel via Agent tool
5. **Monitor** — report each completion as a checkpoint
6. **Merge** — run batch_merge_summaries.py, present final summary table

BATCH.md contains zero SKILL.md logic. It only describes orchestration.
