# Application Question Answerer — Design Spec

**Date:** 2026-04-16
**Status:** Approved

## Problem

When applying to jobs, application forms often include free-text questions (e.g., "Why are you interested in this company?", "Describe your technical experience"). Answering these requires navigating back to the tailored resume outputs and JD to maintain consistency. This is repetitive friction that slows down the application process.

## Solution

A two-part system: the jobcapture Chrome extension captures application questions from form pages, and a Claude Code skill (`/answer-questions`) generates answers using the company's existing tailored resume outputs. Answers are then auto-filled back into the form via the extension.

## Constraints

- No external API calls — all generation runs locally via Claude Code
- Answers are only generated when tailored resume outputs already exist for the company
- Only free-text questions are in scope (not dropdowns, multiple choice, checkboxes)
- Zero-cost — no paid inference APIs

---

## Architecture

### Component Overview

```
Browser (Extension)          Local File System          Claude Code
┌─────────────────┐      ┌──────────────────────┐    ┌─────────────┐
│ content.js       │      │ output/applications/  │    │ /answer-    │
│ - detect questions│─────▶│ {co}_questions.json   │───▶│  questions  │
│ - auto-fill       │◀─────│ {co}_answers.json     │◀───│  skill      │
│                   │      │ {co}_answers.md        │    │             │
│ popup.js          │      │                        │    │ prompts/    │
│ - preview/edit    │      │ output/summaries/      │    │ answer_     │
│ - match company   │      │ output/jds/            │    │ strategies/ │
│                   │      │ output/scripts/        │    │             │
└────────┬──────────┘      │ career_ledger.yaml     │    └─────────────┘
         │                 └──────────────────────┘
         │                 ┌──────────────────────┐
         └────────────────▶│ Jobcapture Backend    │
                           │ (FastAPI - file relay) │
                           └──────────────────────┘
```

### Data Flow

1. Extension detects free-text questions on an application form page
2. Extension auto-matches company name against existing outputs (with manual fallback)
3. User clicks "Answer Questions" — extension sends questions to backend
4. Backend writes `{company_slug}_questions.json` to `output/applications/`
5. User runs `/answer-questions` in Claude Code
6. Skill loads questions file, company outputs (summary, JD, resume script), career ledger, and prompt strategy
7. Skill generates answers respecting character/word limits
8. Skill writes `{company_slug}_answers.json` (for auto-fill) and `{company_slug}_answers.md` (for records)
9. User returns to browser, extension detects answers file via backend
10. User previews/edits answers in the extension panel
11. User clicks "Fill Answers" — extension injects answers into form fields

---

## Section 1: Extension Layer (Question Capture + Auto-Fill)

### Question Detection

The content script scans for free-text form fields on application pages. It extracts:

- **Question text** — from `<label>`, nearby heading, placeholder, or instructional text
- **Field DOM selector** — for auto-fill targeting
- **Character/word limit** — from `maxlength` attribute, counter elements, or instructional text
- **Field type** — `short_text` (single-line input) vs. `long_text` (textarea)

Non-question fields (name, email, phone, address) are excluded via heuristics.

### Company Matching

Uses the same extraction logic already in `content.js` to get the company name from the page. Calls the backend to check if tailored outputs exist:

- **Auto-match found** → proceeds normally
- **No auto-match** → shows a dropdown of previously tailored companies for manual selection
- **No outputs exist at all** → displays "No tailored resume for this company" and stops

### UI Additions

A new "Answer Questions" button in the extension panel, visible when questions are detected and a company match exists. States:

- Questions detected → "Answer Questions" button enabled
- After capture → "Questions captured — run `/answer-questions` in Claude Code"
- Answers available → "Fill Answers" button with answer previews
- After fill → green confirmation with count of fields filled

### Auto-Fill Mechanism

When "Fill Answers" is clicked:

1. Reads answers from backend (`GET /api/applications/{company_slug}/answers`)
2. Locates each form field using the stored `field_selector`
3. Sets field value and dispatches `input` + `change` events (for React/Angular/Vue compatibility)
4. Highlights filled fields briefly (green border flash)
5. Fields that couldn't be matched fall back to fuzzy-matching question text against visible labels
6. Still unmatched fields are flagged in the panel with answer text for manual copy-paste

**Safeguards:**
- Fields with existing content are skipped (no overwrite)
- Answer preview with inline editing before fill
- Selector resilience: stores both CSS selector and question text for fallback matching

---

## Section 2: Question & Answer File Format

### Questions File (`output/applications/{company_slug}_questions.json`)

```json
{
  "company": "Glia",
  "role": "Sales Engineer",
  "application_url": "https://jobs.lever.co/glia/abc123/apply",
  "captured_at": "2026-04-16T10:30:00Z",
  "company_match": {
    "method": "auto",
    "summary_file": "output/summaries/glia.yaml",
    "jd_file": "output/jds/glia.txt",
    "script_file": "output/scripts/generate_glia_resume.js"
  },
  "questions": [
    {
      "id": "q1",
      "text": "Briefly describe your client-facing experience in a technical role.",
      "field_selector": "#question_abc123",
      "char_limit": null,
      "word_limit": 500,
      "field_type": "long_text"
    },
    {
      "id": "q2",
      "text": "Are you comfortable with a hybrid work schedule?",
      "field_selector": "#question_def456",
      "char_limit": 200,
      "word_limit": null,
      "field_type": "short_text"
    }
  ]
}
```

### Answers File (`output/applications/{company_slug}_answers.json`)

```json
{
  "company": "Glia",
  "generated_at": "2026-04-16T10:32:00Z",
  "strategy_used": "default",
  "answers": [
    {
      "id": "q1",
      "field_selector": "#question_abc123",
      "answer": "My client-facing technical experience spans...",
      "char_count": 1847,
      "within_limit": true
    }
  ]
}
```

The `id` and `field_selector` carry through for auto-fill matching. The skill also writes a human-readable `{company_slug}_answers.md` for records (same format as existing application files like `glia_sales_engineer.md`).

---

## Section 3: Claude Code Skill (`/answer-questions`)

### Input Resolution

The skill scans `output/applications/` for `*_questions.json` files without a corresponding `*_answers.json`. If exactly one pending file exists, it auto-selects. If multiple, it asks the user to choose.

### Context Loading

For the matched company, the skill reads:

1. `output/applications/{company}_questions.json` — what to answer
2. `output/summaries/{company}.yaml` — tailored resume content decisions
3. `output/jds/{company}.txt` — original job description
4. `output/scripts/generate_{company}_resume.js` — the actual bullet points on the submitted resume
5. `career_ledger.yaml` — full experience bank for depth beyond the resume

### Prompt Strategy System

The skill loads a strategy file from `prompts/answer_strategies/` (at project root, i.e., `resume_tailoring_skill/prompts/answer_strategies/`). Each strategy defines generation rules:

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

**Extensibility:** Additional strategy files can be created for specific question types (e.g., `why_this_company.yaml`, `technical_experience.yaml`). The skill can auto-classify which strategy fits each question, or strategies can be mapped manually. This is the hook for future prompt refinement or a dedicated skill.

### Output

- `output/applications/{company_slug}_answers.json` — structured answers for auto-fill
- `output/applications/{company_slug}_answers.md` — human-readable markdown for records

---

## Section 4: Backend Additions (Jobcapture FastAPI)

The backend serves as a thin file relay between the extension and the local file system. No database changes, no LLM calls.

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/applications/{company_slug}/questions` | Receives extracted questions from extension, writes to `output/applications/{company_slug}_questions.json` |
| `GET` | `/api/applications/{company_slug}/answers` | Returns answers JSON for auto-fill (404 if not yet generated) |
| `GET` | `/api/applications/{company_slug}/match` | Fuzzy-matches a company name against existing output folders, returns match or candidates for dropdown |
| `GET` | `/api/applications/pending` | Lists question files without corresponding answer files |

All endpoints are file read/write operations against `output/applications/`. No new database models or tables.

---

## Section 5: End-to-End Flow

```
1. You're on an application form (Greenhouse, Lever, etc.)
2. Extension detects free-text questions on the page
3. Extension auto-matches company name → checks if tailored outputs exist
   - No outputs found → "No tailored resume for this company" (stop)
   - Outputs found → "Answer Questions" button appears
4. You click "Answer Questions"
   - Extension sends questions to backend → saved as _questions.json
   - Panel shows: "Questions captured — run /answer-questions in Claude Code"
5. You switch to Claude Code, run /answer-questions
   - Skill finds the pending questions file
   - Loads company summary, JD, resume script, career ledger
   - Loads prompt strategy (default or question-type-specific)
   - Generates answers respecting character/word limits
   - Writes _answers.json + _answers.md
6. You switch back to browser
   - Extension detects answers file exists → "Fill Answers" button appears
   - Panel shows answer preview for each question
   - You review/edit inline if needed
7. You click "Fill Answers"
   - Answers injected into form fields with event dispatching
   - Failed fills flagged for manual copy-paste
8. You review the filled form and submit
```

## Out of Scope

- Multiple choice / dropdown / checkbox questions
- Answer generation without existing tailored resume outputs
- External API calls (all local)
- Modifications to the existing resume tailoring pipeline
- Real-time collaboration or multi-user support
