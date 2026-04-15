# Initialization: Resume Discovery & Career Ledger

**Goal:** Build a Career Ledger — the single source of truth for what the user actually did — structured around **atomic achievements** that map directly to resume bullet points.

**Input:** The **Resume Bank** (.docx) — the comprehensive file containing ALL past experiences. This file often exceeds one page and is the content source for tailoring. `resume_master.docx` is no longer required for formatting.

## Step 1: Scaffold the Career Ledger

Run the scaffold script to extract text from the Resume Bank and generate a YAML skeleton:

```bash
python3 scripts/build_ledger.py --force inputs/resume_bank.docx career_ledger.yaml
```

The script:
1. Extracts plain text from the `.docx` via `pandoc --wrap=none`
2. Splits text into sections (Work Experience, Projects, Education, Skills)
3. Parses entries: role, company, location, dates, and bullet points
4. Extracts metrics from bullet text and classifies their type
5. Auto-detects tools mentioned in each bullet
6. **Merges duplicate entries** (same company across Work Experience and Additional Content sections)
7. Writes a structured YAML file with TODO placeholders for judgment fields

Use `--force` to overwrite an existing ledger without prompting (required for non-interactive agent use).

If the Resume Bank is not at `inputs/resume_bank.docx`, pass the correct path as the first argument.

If the resume content is already visible in the conversation context (as a document attachment) and the script is unavailable, build the ledger manually following the schema below.

## Step 1b: Validate Parsing (Before Filling TODOs)

The script uses heuristic parsing that can fail on non-standard formatting. **Before filling any TODOs**, scan for these common errors:

**Header parsing errors (check every entry):**
- `role` truncated or misspelled (e.g., "Analys" instead of "Analyst") — fix from resume bank text
- `company` contains location fragments (e.g., "Ant Group CA") — split into company + location
- `location` says "TODO" when the resume bank clearly has a location — set manually
- `location` contains company words (e.g., "Packaging Ningbo") — move the company word back

**Structural errors:**
- Duplicate entries for the same role (script merges same-company entries, but non-standard headers like "ADDITIONAL CONTENT" may produce orphan entries with `company: "TODO"`) — merge manually
- `dates` says "TODO" — the date format in the resume bank didn't match `Month YYYY - Month YYYY`
- Bullet split incorrectly (pandoc sometimes breaks mid-sentence) — rejoin

**Quick validation command:**
```bash
grep -n 'TODO\|company:.*TODO\|location:.*TODO\|role:.*TODO' career_ledger.yaml
```

Fix all parsing errors before proceeding to Step 2.

## Step 2: Review and Complete the Scaffold

Open `career_ledger.yaml` and fill in every field marked TODO. The script handles mechanical extraction; the agent handles judgment calls. **Save this file to the working directory.** This file becomes the single source of truth for all future tailoring runs, saving massive token costs by never reading the raw `.docx` again.

**Fields requiring review (in priority order):**
1. `keywords_natural` — organic keywords each achievement naturally supports (CRITICAL: used for scoring and keyword matching in Phase 1-2)
2. `reframe_ceiling` — per-achievement guardrail (CRITICAL: prevents over-claiming in bullet writing)
3. `plausibility_ceiling` — role/project-level guardrail
4. `method` — how the achievement was accomplished (refine from auto-detected tools)
5. `outcome` — the business result or downstream impact
6. `action` — distill raw bullet text to a concise one-sentence description
7. `tools_confirmed` — verify and expand the auto-detected tool list

### CRITICAL DESIGN PRINCIPLE: Atomic Achievements

The ledger stores **individual achievements**, not prose summaries. Each achievement is a pre-parsed XYZ skeleton that maps directly to one resume bullet point:

- `action` = the [X] variable (what was accomplished)
- `metric` + `metric_type` = the [Y] variable (quantified proof)
- `method` = the [Z] variable (how it was done — and the keyword injection zone)

This structure eliminates the need for the agent to re-interpret prose blobs during bullet generation. The agent's job during tailoring is to **select** the right achievements and **dress them in JD vocabulary**, not to decompose narratives from scratch.

### 2a. Work Experience Schema

For each role, extract a header block plus an array of atomic achievements:

```yaml
work_experience:
  - role: "[Exact title from Resume Bank]"
    company: "[Company]"
    location: "[City, State or Remote]"
    dates: "[Start - End]"
    tools_confirmed: [tool1, tool2, tool3]
    plausibility_ceiling: "Role-level guardrail: what framing is honest vs. fabrication for this entire role."
    achievements:
      - id: "[company_short]_[number]"
        action: "One-sentence description of what was accomplished"
        metric: "The specific number, percentage, dollar figure, or scale indicator"
        metric_type: scale | percentage | dollar | time | none
        method: "How it was done — tools, techniques, processes"
        outcome: "The business result or downstream impact (if distinct from action)"
        reframe_ceiling: "Per-achievement guardrail: what can be reframed vs. what would be fabrication"
        keywords_natural: [keyword1, keyword2, keyword3]
```

**Field definitions:**

| Field | Purpose | Used By |
|-------|---------|---------|
| `id` | Unique reference for selection and tracking | Steps 2.1 (scoring), 2.2 (selection), 2.3 (bullet generation) |
| `action` | Maps to [X] in XYZ formula — the achievement | Step 2.3 (bullet generation) |
| `metric` | Maps to [Y] in XYZ formula — the quantified proof | Step 2.3 (metric density check) |
| `metric_type` | Classifies the metric for diversity enforcement | Step 2.5 (audit: diversify metric types) |
| `method` | Maps to [Z] in XYZ formula — the keyword injection zone | Step 2.3 (keyword injection) |
| `outcome` | Business result, used when distinct from action | Step 2.3 (bullet tail) |
| `reframe_ceiling` | Per-achievement plausibility guardrail | Step 2.3 (prevents over-claiming) |
| `keywords_natural` | Organic vocabulary this achievement supports | Steps 1.2 (keyword allocation), 2.1 (scoring) |

**Example — well-structured achievements for a risk analyst role:**

```yaml
work_experience:
  - role: "Risk Management Analyst"
    company: "Ant Group"
    location: "Sunnyvale, CA"
    dates: "Jul 2025 - Dec 2025"
    tools_confirmed: [SQL, Salesforce, Excel, XLOOKUP, pivot tables]
    plausibility_ceiling: "Analyst role operating within existing systems. Can frame as 'translated operational insights into product changes' but cannot claim 'built the platform' or 'engineered the system.'"
    achievements:
      - id: ant_1
        action: "Adjudicated onboarding and risk cases with enforcement decisions"
        metric: "500+ weekly cases, blocked 200+ high-risk applications, froze 100+ compromised accounts"
        metric_type: scale
        method: "SQL alert extraction, Salesforce case management, KYC and sanctions triage"
        outcome: "Maintained onboarding integrity for fintech wallet product"
        reframe_ceiling: "Can reframe as 'case triage workflow' or 'operator decision-making' — cannot claim built the triage system"
        keywords_natural: [KYC, sanctions, risk operations, case triage, enforcement, onboarding]

      - id: ant_2
        action: "Drove rejection transparency logic change with Product team"
        metric: "Reduced application rework from 50% to 30%, cut weekly escalations from 300+ to 200"
        metric_type: percentage
        method: "Root cause analysis in Excel (XLOOKUP, composite keys, pivot tables), data reconciliation"
        outcome: "Product team adopted granular messaging fix"
        reframe_ceiling: "Can frame as 'translating operational pain into product improvement' or 'cross-functional workflow design' — cannot claim owned the product decision"
        keywords_natural: [root cause analysis, rejection logic, cross-functional, Product collaboration, workflow improvement]

      - id: ant_3
        action: "Investigated coordinated merchant abuse patterns"
        metric: "Off-boarded 50+ coordinated high-risk accounts"
        metric_type: scale
        method: "SQL joins and cluster analysis on shared registration addresses and templated domains"
        outcome: "Strengthened onboarding integrity"
        reframe_ceiling: "Can frame as 'link analysis' or 'pattern detection' — cannot claim 'built a fraud detection system'"
        keywords_natural: [link analysis, coordinated abuse, Sybil detection, merchant risk, pattern detection]

      - id: ant_4
        action: "Discovered resubmission failure patterns through data reconciliation"
        metric: "70% of resubmissions had zero field changes, 57% were website-related"
        metric_type: percentage
        method: "Excel data reconciliation with composite keys, XLOOKUP"
        outcome: "Proposed granular messaging fix adopted by Product team"
        reframe_ceiling: "Strong data insight — can frame as 'data-driven product recommendation' or 'UX insight from operational data'"
        keywords_natural: [data reconciliation, resubmission analysis, UX insight, data-driven recommendation]

      - id: ant_5
        action: "Managed client-facing case communications and routing"
        metric: "500+ weekly cases validated for enforcement accuracy"
        metric_type: scale
        method: "Salesforce case routing, applicant inquiry response, cross-department coordination (Product, Compliance, Support)"
        outcome: "Resolved billing and compliance issues, reduced rework"
        reframe_ceiling: "Can frame as 'operator workflow management' or 'stakeholder communication' — cannot claim 'built the Salesforce system'"
        keywords_natural: [Salesforce, client communication, case routing, compliance, operator workflow]
```

### 2b. Independent Projects Schema

Separately catalog any portfolio, personal, or academic projects (NOT projects done within a paid role — those are achievements under Work Experience):

```yaml
independent_projects:
  - project_name: "[Project Name]"
    tools_confirmed: [tool1, tool2]
    link: "GitHub repo, live demo, or portfolio URL (if available)"
    plausibility_ceiling: "Project-level guardrail for the entire project."
    achievements:
      - id: "[project_short]_[number]"
        action: "What was built or accomplished"
        metric: "Dataset size, model accuracy, records processed, etc."
        metric_type: scale | percentage | dollar | time | none
        method: "Technical implementation details"
        outcome: "Result or finding"
        reframe_ceiling: "Per-achievement guardrail"
        keywords_natural: [keyword1, keyword2]
```

Look for projects in: the resume itself, GitHub links in the resume header, portfolio URLs, or anything the user mentions.

### 2c. Education Schema

```yaml
education:
  - institution: "[University Name]"
    location: "[City, State]"
    degree: "[Full degree name]"
    gpa: "[GPA if listed]"
    graduation: "[Date]"
    relevant_coursework: [course1, course2, course3]
    keywords_natural: [keyword1, keyword2]
```

### 2d. Skills Inventory

Extract every confirmed tool, language, framework, and methodology into a flat list. This is the master list from which the Skills section is constructed during tailoring.

```yaml
skills_confirmed:
  languages: [Python, SQL, JavaScript, Node.js]
  tools: [Tableau, Excel, Salesforce, Shopify]
  frameworks: [Vertex AI, Gemini, Google ADK, Scikit-learn, Pandas, NumPy]
  methods: [ETL pipelines, data reconciliation, regression analysis, prompt engineering]
```

**The Plausibility Rule (ENFORCED ON EVERY ENTRY):** When building this ledger, apply this test to every achievement: "Would the original hiring manager at that company recognize this as something the candidate actually did?" Never invent experience, metrics, or responsibilities. Only document what is explicitly stated or can be safely inferred from the text.

**Metric extraction rule:** If the Resume Bank contains a specific number, record it exactly. If no number exists for an achievement, set `metric_type: none` and leave `metric` as a brief scale description (e.g., "daily operations" or "multiple data sources"). Do NOT invent numbers during ledger construction — metric fabrication happens here more than anywhere else.

## Step 3: Verify

Before proceeding to Phase 1, verify:

1. **No TODO placeholders remain** — run `grep -c "TODO" career_ledger.yaml` and confirm the count is 0.
2. Every role has at least 2 achievements with `metric_type` other than `none`.
3. Every achievement has a non-empty `keywords_natural` array (not `[TODO]`).
4. Every achievement has a non-empty `reframe_ceiling` (not the placeholder text).
5. `skills_confirmed` captures every tool mentioned anywhere in the Resume Bank.
6. No duplicate entries exist for the same role (merged in Step 2).

Do not proceed to Phase 1 until this file passes all checks.
