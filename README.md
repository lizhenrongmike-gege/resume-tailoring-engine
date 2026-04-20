# Resume Tailoring Engine

An end-to-end, agent-driven pipeline that takes a comprehensive **Resume Bank** and a **Job Description** and produces an ATS-optimized, one-page, company-specific `.docx` resume — with an automated grader, batch mode, and a job scanner that finds openings worth applying to.

The project is built as a family of **Claude Code skills** (`SKILL.md`, `BATCH.md`, `GRADE.md`, `gap-closer/`) plus supporting Python and Node scripts.

---

## What you get

| Component | Purpose | Entry point |
|---|---|---|
| **Resume tailoring** | Turn one JD into a surgically tailored, ATS-safe `.docx` | `SKILL.md` |
| **Batch mode** | Process many JDs from an Excel file in parallel | `BATCH.md` |
| **Quality grader** | Score a generated resume on 8 dimensions (4 automated, 4 agentic) | `GRADE.md` + `scripts/grade_resume.py` |
| **Gap closer** | Diagnose career gaps vs. a target role and output a 30-day plan | `gap-closer/SKILL.md` |
| **Job scanner** | Discover relevant openings via Greenhouse / JobSpy / web search, rank with Claude | `jobscan/scan.py` |
| **JobCapture** | Capture JDs from the browser, manage them via a dashboard, and feed batch mode | `jobcapture/` |

---

## Prerequisites

The skill orchestrates several system tools — this is not a pure-Python project.

**System packages**

| Tool | Used for | macOS | Debian/Ubuntu |
|---|---|---|---|
| `pandoc` | doc conversion | `brew install pandoc` | `apt install pandoc` |
| `libreoffice` | `.docx` → PDF for page-fit verification | `brew install --cask libreoffice` | `apt install libreoffice` |
| `poppler` (`pdfinfo`, `pdftotext`) | PDF inspection | `brew install poppler` | `apt install poppler-utils` |
| `node` ≥ 18 | runs the `.docx` generator (`docx` npm package) | `brew install node` | `apt install nodejs npm` |
| `python3` ≥ 3.10 | scanner, grader, batch orchestration | `brew install python` | `apt install python3` |

**Credentials** — a Claude API key (`ANTHROPIC_API_KEY`). Get one at [console.anthropic.com](https://console.anthropic.com/). Any LiteLLM-supported provider works; see `.env.example`.

---

## Install

```bash
git clone https://github.com/lizhenrongmike-gege/resume-tailoring-engine.git
cd resume-tailoring-engine

# System + Node deps (macOS / Debian auto-detected)
bash setup.sh

# Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install openpyxl pyyaml python-docx litellm anthropic click pandas

# Configure
cp .env.example .env
# then edit .env and paste your ANTHROPIC_API_KEY
```

> `requirements.txt` is a dependency **manifest** (system + node + python), not a pip lockfile. Install Python packages with the `pip install` line above.

---

## Quickstart — tailor one resume

1. **Drop your Resume Bank** (a `.docx` containing *all* past experiences — can be multi-page) into `inputs/resume_bank.docx`. The `inputs/` folder is gitignored; it stays on your machine.
2. **Open Claude Code** in this repo and trigger the skill with any of:
   - `tailor my resume`
   - `here is a JD:` followed by the job description
   - `new job application`
3. The skill will read `SKILL.md`, verify dependencies, analyze the JD, tailor bullets, and write a `.docx` to `output/doc/`.
4. **Grade the result** with: `grade this resume` (reads `GRADE.md`).

---

## Quickstart — batch mode

Put an Excel file at `inputs/batch_jds.xlsx` with:
- Column A: company name
- Column B: JD text

Then in Claude Code:
```
batch tailor
```
Variants: `batch tailor auto` (reads `inputs/batch_jds_auto.xlsx` from the scanner) and `batch tailor manual` (reads `inputs/batch_jds_manual.xlsx` from the browser extension).

Outputs land in `output/doc/`, `output/pdf/`, and `output/summaries/`.

---

## Quickstart — job scanner

Scans Greenhouse company boards, JobSpy aggregators, and web search, then screens + ranks hits with Claude using your profile.

```bash
python3 -m jobscan.scan --help
```

Configure which tiers are live and which models to use via `.env` (see `.env.example`).

---

## Quickstart — JobCapture (browser → dashboard → batch)

JobCapture is a three-part companion app that lets you clip job descriptions from any careers page and queue them for batch tailoring. It lives under `jobcapture/` and has three components:

- **Backend** — FastAPI + SQLite (`jobcapture/backend/`)
- **Dashboard** — Vite + React UI (`jobcapture/dashboard/`)
- **Extension** — Chrome extension for one-click capture (`jobcapture/extension/`)

### 1. Start the backend

```bash
cd jobcapture/backend
python3 -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements.txt                      # first time only
uvicorn app.main:app --reload
```

Verify at http://localhost:8000/api/health — you should see `{"status":"ok"}`. Interactive API docs at http://localhost:8000/docs.

If port 8000 is already taken by a stuck process:

```bash
lsof -ti :8000 | xargs kill -9
```

### 2. Start the dashboard

In a new terminal:

```bash
cd jobcapture/dashboard
npm install      # first time only
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). The dashboard talks to the backend on `localhost:8000`.

### 3. Load the Chrome extension

1. Go to `chrome://extensions`
2. Turn on **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select `jobcapture/extension/`
4. Pin the extension, then click its icon on a job posting page to capture the JD

Captured JDs flow into the backend, show up in the dashboard, and can be exported into the Excel files consumed by `batch tailor manual`.

---

## Project layout

```
.
├── SKILL.md               # Primary tailoring skill (v4)
├── BATCH.md               # Batch-processing skill
├── GRADE.md               # Quality grader skill
├── gap-closer/            # Career-gap analysis skill
├── jobcapture/            # Browser extension + dashboard + FastAPI backend
├── jobscan/               # Job discovery + ranking pipeline
│   ├── scan.py            #   CLI entry point
│   ├── connectors/        #   Greenhouse, JobSpy, web search
│   ├── ranker.py          #   Claude-powered screening & ranking
│   └── profile_*.yaml     #   Candidate profile used for matching
├── scripts/               # Python/Node utilities (grader, ledger, template)
├── references/            # Environment setup, grading rubric, init guides
├── tests/                 # pytest + fixtures
├── docs/                  # Public docs (per-project plans live in a private dir)
├── inputs/     (gitignored) resume bank, JD batches — your private data
├── output/     (gitignored) generated resumes, PDFs, summaries
└── .env        (gitignored) your secrets
```

---

## Testing

```bash
pytest tests/ -v
node tests/test_resume_template_spacing.js
```

Sample fixtures in `tests/fixtures/` let the suite run without touching your real Resume Bank.

---

## Privacy

The following are **gitignored** on purpose — do not commit them:

- `inputs/`, `output/`, `reports/`, `tmp/` — your runs
- `career_ledger.yaml` — your lived career history
- `.env` — your API keys
- Any `.docx` / `.xlsx` in the repo root (test fixtures under `tests/fixtures/` are whitelisted)

Open-source contributors: please do not add personal resumes, real company names, or PII to test fixtures.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pandoc: command not found` | Re-run `bash setup.sh` or install manually |
| `node -e "require('docx')"` fails | From repo root, run `npm install` |
| `libreoffice` missing | The pipeline still produces `.docx`; page-fit PDF verification is skipped |
| `ANTHROPIC_API_KEY not set` | `cp .env.example .env` and paste your key |
| Scanner returns 0 jobs | Check `TIER1/2/3_ENABLED` and `JOBSPY_*` filters in `.env` |

---

## License

AGPL-3.0 — see `LICENSE`.
