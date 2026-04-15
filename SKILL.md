---
name: codex_resume_tailoring_machine_v5
description: "Tailors a resume to a specific job description (JD) for maximum ATS score and interview callback rate. Requires a Resume Bank (.docx with all past experiences, for content) and a JD (pasted in chat). Uses a hardcoded ATS-safe formatting profile. Use this skill whenever the user mentions resume tailoring, job applications, JD matching, ATS optimization, or provides a job description and wants their resume customized. Trigger phrases: 'tailor my resume', 'new job application', 'here is a JD', 'optimize for ATS'. Handles the full pipeline: initialization, JD analysis, gap resolution, keyword allocation, scoring, selection, bullet generation, audit, and .docx export."
---

# Resume Tailor — ATS-Optimized Resume Engineering (v5)


## Quick Start

1. **Read this entire SKILL.md first.** Do not start writing until you've read all sections.
2. **Verify dependencies** (see Phase 0a). Install if missing.
3. **Locate inputs** — check `inputs/` directory, then ask for anything missing:
   - **Resume Bank** (.docx) — all past experiences. Look for `inputs/resume_bank.docx`.
   - **Job Description (JD)** — pasted by the user.
4. **Run the pipeline** below in order: Initialize → Analyze → Allocate → Resolve → Classify → Select → Write → Audit → Export → Verify.

---

## Phase 0: Setup & Initialization

### 0a. Environment Setup (run once)

**Required tools:** `python3`, `pandoc`, `node` + `docx` (npm), `libreoffice`, `pdfinfo`. All must be installed before proceeding.

**→ See [references/environment_setup.md](references/environment_setup.md) for install commands and verification.**

### 0b. Career Ledger Initialization (run once)

**Goal:** Build a Career Ledger (single source of truth for the user's experience) from the **Resume Bank** and save it as `career_ledger.yaml`. The ledger uses an **atomic achievement schema** where each achievement is a pre-parsed XYZ skeleton with its own metric, method, keywords, and plausibility guardrail.

**If `career_ledger.yaml` already exists** in the working directory, skip this step entirely and use the existing file.

**If it does not exist**, scaffold it using the build script, then review:

1. **Run the scaffold script:**
   ```bash
   python3 scripts/build_ledger.py --force inputs/resume_bank.docx career_ledger.yaml
   ```
   This extracts text via pandoc, parses sections, extracts metrics, merges duplicate company entries, and writes a YAML skeleton with TODO placeholders.

2. **Validate parsing** — check for header parsing errors (truncated roles, misplaced location words, orphan entries). See [references/initialization.md](references/initialization.md) Step 1b.

3. **Fill in every TODO** — prioritize `keywords_natural` and `reframe_ceiling` (used in Phases 1-2). See [references/initialization.md](references/initialization.md) Step 2.

4. **Verify** using the checklist in [references/initialization.md](references/initialization.md) Step 3.

**→ See [references/initialization.md](references/initialization.md) for full schema documentation and field definitions.**

### 0c. ATS Format Profile

Formatting is locked in `scripts/resume_template.js` — the single source of truth for all formatting, spacing, and layout. Do not derive formatting from any external file, user template, or inline profile object. The agent imports this module in Phase 3 rather than rewriting the profile each run. It exports:
- `buildDocument(content, outputPath)` — generates the .docx from a content object
- `estimatePageFill(content)` — predicts page fill (fillPercent, verdict, totalBullets, totalBulletChars) without generating a file

---

## Phase 1: JD Analysis, Keyword Allocation & Gap Resolution

**Goal:** Parse the JD, build a keyword placement plan, identify hard-requirement gaps, and resolve them BEFORE any content selection begins.

### Step 1.1: Extract JD Elements

| Element | What to Extract |
|---------|----------------|
| Exact job title | Use as resume summary anchor |
| Top 10-15 keywords | Ranked by frequency in JD text |
| Hard requirements | Must-haves (years, specific skills, certifications) |
| Soft preferences | Nice-to-haves ("plusses", "preferred") |
| Core business driver | Revenue / Cost Reduction / Efficiency / Compliance |
| Experience level | Entry / Mid / Senior — from years required + seniority language |
| Domain context | Industry, company stage, team size |

### Step 1.2: Build Keyword Allocation Table

**BEFORE scoring or selecting any content**, map every JD keyword to a specific placement target. This prevents silent keyword omission — the most common tailoring failure.

For each keyword, search `career_ledger.yaml` — each achievement's `keywords_natural` array and `tools_confirmed` lists — for matching evidence. If a keyword matches NO achievement and NO entry in `skills_confirmed`, mark Ledger Source as **GAP**.

**Rules:**
- Keywords appearing 3+ times in JD are **critical**.
- Every hard-requirement keyword MUST have at least one placement target.
- Target: 25-35 total keywords. Below 25 = insufficient ATS visibility. Above 35 = keyword stuffing risk.
- For every acronym keyword, note which bullet carries the first-mention expansion.

**Persist the table** as `jd_keywords.yaml`:

```yaml
keywords:
  - keyword: "TypeScript"
    type: hard_req          # hard_req | preferred | critical
    placement: ["skills", "bullet:nuonc_1"]
    ledger_source: ["achievement_id"]   # or ["GAP"]
    acronym_first_mention: null         # bullet ID that carries expansion, or null
    status: PENDING                     # PENDING → PLACED | MISSING
```

Update each keyword's `status` to PLACED as you write the bullet that carries it.

### Step 1.3: Gap Resolution

**For each keyword marked as GAP:**

**A. Search for adjacent/transferable skills** — check every achievement's `keywords_natural`, `method`, and `tools_confirmed`. Map transferable skills explicitly with a note: "via [adjacent_skill] — transferable, not exact." Add to Skills line with honest framing. The reframed keyword counts toward the 25-35 target but should be flagged in the fit diagnosis.

**B. If NO adjacent skill exists** — flag to user: "The JD requires [X]. Your Resume Bank has no evidence. Options: (a) tell me about relevant work not in the bank, (b) proceed without — reduces ATS match, (c) add 'Currently learning' if accurate."

**WAIT for user input on hard-requirement gaps before proceeding.** This is the ONE exception to "do not wait" — a missing hard requirement is a candidacy problem, not a tailoring problem.

**NEVER inject a hard-requirement keyword the candidate cannot substantiate.** This overrides all keyword injection pressure.

### Step 1.4: Fit Assessment & Strategy

Count from the allocation table: how many hard requirements are STRONG (direct evidence with metrics), MODERATE (transferable or unquantified), or GAP?

- **80-100% covered:** Strong match. Proceed.
- **60-79%:** Moderate match. Note 1-2 gaps and plan reframing.
- **Below 60%:** Weak match. Tell the user honestly. Ask if they want to proceed.

Output a **concise** fit diagnosis (max 150 words): target role, fit score, gaps and how resolved, which roles are emphasized vs. cut, role ordering (strongest JD overlap first).

**If no unresolved hard-requirement gaps remain**, proceed immediately to Phase 2.

---

## Phase 2: Sequential Content Tailoring

**Goal:** Tailor the resume content through a strict sequence: classify → estimate fill → select and assign space → write bullets → audit. Do not make selection, wording, and audit decisions simultaneously.

---

### CONTENT BUDGET — HARD CONSTRAINTS

Check this table BEFORE starting and AFTER Steps 2.2, 2.4, and 2.5. If any step's output violates these numbers, fix it before moving on.

| Constraint | Min | Default | Max |
|---|---|---|---|
| Roles + projects on page | 4 | 5 | 6 |
| Total bullets | 14 | **17** | 18 |
| Lead role bullets | 4 | 4 | 5 |
| Supporting role bullets | **2** | 2 | 3 |
| Supporting project bullets | **2** | **3** | 3 |
| Words per bullet | 15 | mixed | 36 |

**BIAS TOWARD THE UPPER END of each range.** Underfilling is harder to fix after Phase 3 generation; overflow is easy to trim. When in doubt, include more content.

**Supporting roles get 2 bullets by default.** Expand to 3 when the role has strong JD evidence and page space allows.

**Supporting projects get 3 bullets by default.** Drop to 2 only if page space is tight or the project lacks a third distinct achievement.

**Page-fill rule:** Bullet count is a rough heuristic; **total character count is the real predictor** because long bullets wrap to multiple lines. Use `estimatePageFill(content)` to verify before generating. Phase 3 can trim 1-2 bullets if the page overflows; adding bullets after export requires restarting Phase 2. **Always overshoot.**

> **VOLUME FLOOR:** If at any point total items < 4 OR total bullets < 14, promote HOLD items or add bullets before continuing. A full page is always better than a half-empty page. Formal enforcement is in Step 2.5.

---

### Resume Structure

Fixed section order: Name → Contact → Professional Summary → Skills → Work Experience → Selected Projects (if any) → Education. All formatting is in `scripts/resume_template.js`. Phase 2 is about **content only**.

---

### Step 2.1: Classify Every Role and Project

Classify **every** role and **every** project from `career_ledger.yaml` against the JD. Use each achievement's `keywords_natural` array to measure keyword overlap — do not estimate from role-level prose.

**Gate check (pass/fail):**
- Does this item contain ANY hard-requirement keyword in any achievement's `keywords_natural`?
- If NO: automatic HOLD unless fewer than 4 items pass the gate.

**Classify each item:**

| Classification | Criteria (ALL must be true) |
|---|---|
| **STRONG** | ≥2 achievements have hard-requirement keywords in `keywords_natural` AND ≥1 has `metric_type` ≠ `none` |
| **MODERATE** | ≥1 achievement has hard-requirement keywords OR has transferable evidence with metrics |
| **WEAK** | Passed gate check but only 1 matching keyword with no quantified achievements |

**Within the same tier**, break ties by: (a) distinct hard-requirement keywords matched, then (b) achievements with `metric_type` ≠ `none`.

**Project protection rule:** If a project is classified higher than the weakest role, the project must replace that role or be added ahead of it.

**Output:** Scorecard table: Item | Type | Classification | Hard-Req Keywords Matched | Metric Achievements | Why.

---

### Step 2.2: Select Items AND Assign Space Budget

**These are one decision.** Selection without bullet counts is incomplete; bullet counts without selection are meaningless.

#### Selection: Include-First Logic

**Start with everything that passed the gate check INCLUDED.** Then selectively demote:

1. Rank by classification (STRONG first). Break ties using Step 2.1 criteria.
2. If total items ≤ 6 and estimated bullets at default budget ≤ 18: **keep everything.**
3. If over: demote WEAK first, then lowest MODERATE, until 5-6 items.
4. Only mark `CUT` if WEAK AND you have 5+ MODERATE-or-better items.

**Before demoting any project**, compare against the weakest selected role. If the project has stronger JD evidence, keep the project and demote the role.

#### Space Assignment

Assign exact bullet counts AND specific `achievement_id`s per bullet:

| Position | Default Bullets | Achievement Selection |
|---|---|---|
| Lead role | 4 | 4 most JD-relevant (prioritize hard-req keywords + metrics) |
| Supporting role | 2 | 2 most JD-relevant |
| Supporting project | 3 | 3 most JD-relevant |

Pick achievements with (a) metrics for the first two slots, (b) JD keywords in `keywords_natural`, (c) diverse `metric_type` across the page.

#### Reframing Plan

For each selected item, note how its vocabulary shifts to echo JD language. Check `reframe_ceiling` from each achievement to set limits. This plan guides bullet writing in Step 2.3.

#### Page Fill Check (BEFORE writing bullets)

**Quick check:** 17-18 bullets with STANDARD-length dominant = well-filled. 14-16 = likely underfilled (promote from HOLD or expand lead to 5). 19+ = likely overflow.

**Precise check:** Build a preliminary `content` object with placeholder bullets at target word counts and run `estimatePageFill(content)`:
- **fillPercent 80-100%** = OK.
- **< 80%** = UNDER. Add content before writing.
- **> 100%** = OVER. Cut an item or reduce bullets.
- **95-105%** = near boundary (~3-5% margin of error); proceed but verify with PDF.

If underfilled, add content BEFORE writing. It's much easier to cut than to add later.

**Output:**
```text
Selection & Budget
- Lead: [role] → [X] bullets (achievement_ids: ...)
- Support: [role] → [X] bullets (achievement_ids: ...)
TOTAL: [X] items | [X] bullets | Est. [X] chars
estimatePageFill: fillPercent [X]% | verdict [UNDER / OK / OVER]
Selected / Held / Cut with reasons
```

---

### Step 2.3: Generate Final Bullets

Generate bullets for each selected item using the **specific achievements** chosen in Step 2.2. Each bullet is constructed from its achievement's pre-parsed fields:

- `action` → [X] slot (rewrite with approved verb + JD vocabulary)
- `metric` → [Y] slot (place in first 8-10 words)
- `method` → [Z] slot (inject JD keywords from allocation table)

**Produce EXACTLY the assigned count per item.** If you can't find enough distinct achievements, flag it — never silently reduce the count.

Before writing any bullet, check the achievement's `reframe_ceiling`.

#### Action Verb Guidelines

**Every bullet MUST begin with a strong past-tense action verb.** Vary verbs across the page — no verb should appear more than twice.

| Category | Verbs |
|----------|-------|
| Build & Create | Built, Designed, Developed, Created, Architected, Launched, Implemented |
| Technical | Engineered, Automated, Deployed, Configured, Integrated, Migrated, Scaled |
| Analysis & Insight | Analyzed, Identified, Investigated, Modeled, Evaluated, Diagnosed, Mapped |
| Improvement | Optimized, Streamlined, Reduced, Consolidated, Refined, Simplified, Resolved |
| Leadership & Drive | Led, Drove, Spearheaded, Orchestrated, Directed, Coordinated, Established |
| Delivery & Impact | Delivered, Generated, Accelerated, Expanded, Produced, Secured, Negotiated, Constructed, Conducted |
| Process & Structure | Standardized, Formulated, Restructured, Transformed, Overhauled, Unified |

**NEVER use:** Assisted, Responsible for, Helped, Participated in, Handled, Maintained, Utilized, Supported, Worked on, Contributed to.

**Variety rule:** After writing all bullets, check — if any verb appears 3+ times, replace one instance with a synonym from the table.

#### Bullet Formula: XYZ

```
[X] Approved verb + achievement  →  [Y] Quantified metric  →  [Z] Method/tools/context (KEYWORD INJECTION ZONE)
```

#### Bullet Length Templates (MANDATORY)

Each bullet must follow one of these templates. Assign a template to each bullet BEFORE writing it.

**SHORT SCAN ANCHOR (15-20 words, ~90-130 chars):**
```
Structure: [Approved verb] + [metric in first 8 words] + [by/via] + [one method phrase].
Rule: ONE clause. No commas except inside a metric. Metric in first 8 words.
```

**STANDARD (22-28 words, ~140-185 chars):**
```
Structure: [Approved verb] + [achievement with metric] + [method with 1-2 JD keywords].
Rule: TWO clauses max. One comma-separated list of max 2 items.
```

**LONG (30-36 words, ~190-240 chars):**
```
Structure: [Approved verb] + [achievement] + [metric] + [method] + [distinct outcome].
Rule: Only when outcome is distinct from achievement AND adds material JD proof.
      THREE clauses max. Max 1 long bullet per role. Max 2 across entire page.
```

**MANDATORY LENGTH PATTERN PER ROLE:**
```
Lead role (4 bullets):   SHORT → STANDARD → STANDARD → SHORT or STANDARD
Lead role (5 bullets):   SHORT → STANDARD → STANDARD → SHORT → STANDARD
Supporting role (2):     SHORT → STANDARD
Supporting project (2):  SHORT → STANDARD
Supporting project (3):  SHORT → STANDARD → SHORT or STANDARD
```

**Page rhythm constraints:** At least 4 SHORT scan anchors across the page. Most bullets in the 22-28 word band. Max 2 LONG bullets total. If 70%+ of bullets land in the same 10-word band, rewrite for contrast.

#### Metric Placement & Density

- Put the metric in the **first 8 words** of every quantified bullet.
- Use the `metric` field from the selected achievement — do not invent numbers.
- First bullet in each role MUST be quantified.
- **70%+ of bullets must contain numerical data.** Count after writing all.
- Mix `metric_type` values across the page. If all are `percentage`, rewrite one using scale.
- If achievement has `metric_type: none`, keep bullet unquantified. NEVER fabricate.

#### Keyword Injection

- Use `jd_keywords.yaml` as the injection checklist.
- For each bullet, check which keywords are assigned to this bullet's placement target.
- After writing each bullet, update the keyword's `status` to PLACED in `jd_keywords.yaml`.
- Place JD keywords in the [Z] slot (method/context).
- Use the achievement's `keywords_natural` as a bridge — inject semantically related JD keywords.
- **Acronym expansion:** First mention of any acronym: spell out in full + abbreviation. Track to avoid double expansion.
- No invisible text, keyword stuffing, or standalone keyword lists.

#### Clause Load

- One bullet = one core achievement. Avoid stacking grocery lists.
- If a bullet has 3+ comma-separated items or multiple list clusters plus an outcome, split or trim.

Proceed to Step 2.4. All volume, length, and keyword checks are consolidated in Step 2.5 — do not audit here.

---

### Step 2.4: Write the Summary and Skills Last

Only after final bullets are locked.

#### Professional Summary

- **Maximum 45 words.**
- Sentence 1: identity statement using the **exact JD title** verbatim.
- Sentence 2: 2-3 proof points from the final selected evidence only.
- Rewrite from scratch for every JD. No verbose soft skills.
- Must contain at least 2 critical keywords from `jd_keywords.yaml`.

#### Skills Section

- 1-2 lines max. **Front-load the top 5-8 JD keywords.**
- Only include skills proven by selected content OR confirmed in `skills_confirmed`.
- Reorder per JD emphasis — first 3-4 skills = JD's most-mentioned technologies.
- NEVER include soft skills. Show through bullets.
- If a JD hard requirement was resolved via adjacent skill in Step 1.3, include the adjacent skill (not the fabricated skill).

---

### Step 2.5: Final Content Audit

Audit and patch only — do not rewrite from scratch.

#### Quality Checks
- Hard requirements covered where truthful
- Every bullet checked against its `reframe_ceiling`
- No fabricated metrics or invented experience
- No keyword stuffing or low-value repetition
- Clause-heavy bullets split or trimmed
- Consistent date format across all entries (MM/YYYY or Month YYYY — pick one, use identically)
- Projects not unfairly excluded vs. weaker roles
- **Strict Sectioning:** Selected projects MUST appear under "Selected Projects" heading, never under "Work Experience"

#### Metric Checks
- 70%+ bullets quantified (count: __/__ = __%)
- First 2 bullets per role quantified (when `metric_type` ≠ `none`)
- `metric_type` diversity across page
- Metrics in first 8 words of each quantified bullet

#### Keyword Checks (from `jd_keywords.yaml`)
- Re-read the file. For every PENDING keyword, search final bullets and Skills — update to PLACED or MISSING.
- If > 5 keywords MISSING, revise bullets or Skills before proceeding.
- Total PLACED: target 25-35.
- All acronyms expanded on first mention.
- Exact JD title appears in summary.
- Save the updated file.

#### Action Verb & Volume Checks
- Every bullet starts with an approved verb from the lexicon (no passive or adverb openers)
- Total items ≥ 4, total bullets ≥ 14
- At least 4 SHORT (15-20 word) bullets
- Majority STANDARD (22-28 words), max 2 LONG (>28 words)
- Lead role ≥ 4 bullets, supporting roles = 2 each, projects = 2-3 each

**If any check fails, fix it now.** Do not pass non-compliant content to Phase 3.

---

## Phase 3: Export to .docx

**Goal:** Generate a professionally formatted, ATS-compliant, one-page Word document.

### Step 1: Verify Dependencies

```bash
node -e "require('docx'); console.log('docx OK')"
```
If not installed: `npm install docx`.

**CRITICAL:** Never use `TabStopPosition.MAX` — it defaults to A4 width (not US Letter). The shared module handles this correctly.

### Step 2: Build the Content Object

Populate a `content` object with the tailored data from Phase 2. This is the ONLY thing the agent writes — formatting is locked in `scripts/resume_template.js`.

```javascript
const content = {
  name: "Candidate Name",
  contact: [
    "City, State | email@example.com | 555-123-4567",
    "linkedin.com/in/handle | github.com/handle",
  ],
  summary: "Professional summary text (max 45 words)...",
  skills: "Skill1, Skill2, Skill3, ...",
  workExperience: [
    {
      company: "Company Name",
      location: "City, State",
      title: "Job Title",
      dates: "MM/YYYY - MM/YYYY",
      bullets: ["First bullet...", "Second bullet..."],
    },
  ],
  selectedProjects: [
    { name: "Project Name", dates: "MM/YYYY", bullets: ["..."] },
  ],
  education: {
    school: "University Name",
    location: "City, State",
    degree: "Degree, Minor",
    date: "MM/YYYY",
    details: "GPA: X.X/4.0 | Coursework: ...",
  },
};
```

### Step 3: Estimate Page Fill, Then Generate

```javascript
const path = require("path");
const { buildDocument, estimatePageFill } = require("./scripts/resume_template");

const estimate = estimatePageFill(content);
console.log(`Page fill: ${estimate.fillPercent}% | ${estimate.totalBullets} bullets | ${estimate.verdict}`);
if (estimate.verdict === "OVER") console.warn("WARNING: exceeds one page. Trim bullets.");
if (estimate.verdict === "UNDER") console.warn("WARNING: underfilled. Add content.");

const outFile = path.join(__dirname, "output", "doc", "Company_Role_Resume.docx");
buildDocument(content, outFile);
```

Save as `output/generate_[company]_resume.js` and run with `node`.

**Do NOT redefine the profile, helper functions, or document structure.** The shared module handles all formatting. The agent's only job is to populate `content` and act on the `estimatePageFill` verdict.

### Step 4: Validate and Verify One Page (MANDATORY — NEVER SKIP)

```bash
# Validate .docx opens
pandoc ./output_resume.docx -t plain > /dev/null && echo "Valid" || echo "Corrupt"

# Convert to PDF and check page count
libreoffice --headless --convert-to pdf ./output_resume.docx
pdfinfo ./output_resume.pdf | grep Pages
```

**Two-stage PDF verification:**

**Stage 1 — Density gate:**

```bash
pdftotext ./output_resume.pdf - | grep -c .
```

If the line count is below 66, the resume fails Stage 1. Return to Step 2.2 and add content (promote HOLD items, expand lead role, add project bullets). Re-run `estimatePageFill` → regenerate → re-render. Repeat until line count ≥ 66 or no truthful expansion remains.

**Stage 2 — Page gate (only entered after Stage 1 passes):**

```bash
pdfinfo ./output_resume.pdf | grep Pages
```

If pages == 1 → **PASS**.

If pages > 1, apply fixes in order, then regenerate and re-check page count:
1. Cut or merge weakest metric-free or clause-overloaded bullets
2. Compress summary to 2 lines
3. Reduce supporting projects from 3 to 2 bullets
4. Cut weakest role entirely
5. Last resort: edit `scripts/resume_template.js` spacing (reduce `section.before` 100→80, `bullet.after` 10→5)

Repeat Stage 2 until pages == 1 or no safe trim remains.

**Rules:**
- Stage 1 must be satisfied before Stage 2 begins.
- Once Stage 2 begins, page count is the only active gate.
- Do NOT re-trigger the 66-line requirement after trimming starts.

### Step 5: Deliver to User

Save as `[Company]_[Role]_Resume.docx`. Share with a brief summary of key tailoring decisions (3-5 sentences max).

---

## Critical Accuracy Rules (Override Everything)

These rules are NON-NEGOTIABLE and override any JD keyword pressure:

1. **Never fabricate metrics.** If a real number doesn't exist in the achievement's `metric` field, keep the bullet unquantified.
2. **Never invent experience.** Only reframe what exists in the Career Ledger or what the user confirms.
3. **The Plausibility Rule:** Check each achievement's `reframe_ceiling` before writing. Would the original hiring manager recognize this?
4. **Accomplishments over duties.** Every bullet must prove impact, not describe a job function.
5. **If the user corrects a claim, accept it immediately.**
6. **Never inject a keyword the candidate cannot substantiate.** A missing keyword beats a fabricated claim.
