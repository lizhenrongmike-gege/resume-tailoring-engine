---
name: gap-closer
description: >
  Analyzes gaps between a candidate's career profile (career_ledger.yaml) and a target
  job description or role archetype, then produces a specific, hyper-personalized 30-day
  action plan to close those gaps. Two modes: (1) Single-JD mode — user pastes a specific
  job description. (2) Role-type mode — user names a role archetype (e.g., "Agentic AI
  Engineer", "Data Analyst", "Operations Analyst"). Every action in the output plan bridges
  FROM an existing skill or project in the ledger TO the gap — no generic advice.
  Use when the user asks: 'analyze my gaps', 'what am I missing for [role]', 'close the gap',
  'how do I qualify for', '30-day plan', 'what should I learn', 'gap analysis for',
  'skill gap', 'what skills do I need', 'how to get this job'.
---

# Gap Closer — Career Gap Analysis & 30-Day Action Plan

## Quick Start

1. Read this entire file before starting.
2. Determine mode: **Single-JD** (user pastes a JD) or **Role-type** (user names a role).
3. Read `career_ledger.yaml` in full — this is the single source of truth.
4. **Role-type mode only:** Run Step 1c (Market Research Synthesis) — search 5-8 real JDs and merge findings with the archetype baseline before any gap analysis.
5. Run the 4-phase pipeline in order.
6. Output two files: structured YAML + readable markdown action plan.

---

## Phase 1: Input & Profile Loading

### 1a. Read Career Ledger

Read `career_ledger.yaml` completely. Build a mental profile snapshot:
- All `skills_confirmed` (languages, tools, frameworks, methods)
- All `tools_confirmed` per role and project
- All `keywords_natural` arrays across every achievement
- All `reframe_ceiling` constraints (what can and cannot be claimed)
- Strongest evidence areas (roles/projects with most quantified achievements)

### 1b. Determine Mode and Extract Requirements

**Single-JD mode** (user provided a JD):
Extract the following from the JD:
- `target_title` — exact job title string
- `company` — company name
- `hard_req` — explicitly required skills/tools (deal-breakers if missing)
- `critical` — strongly preferred or frequently mentioned skills
- `preferred` — nice-to-have skills
- `cultural` — signals about values, work style, community (e.g., "we value open-source", "bias for written communication")
- `domain_context` — industry, business model, scale signals
- `experience_signals` — years required, seniority level, team size

**Role-type mode** (user named a role):
1. Check `references/role_archetypes.yaml` for a matching archetype by `id`, `title`, or `also_known_as`.
2. If found: use that archetype's requirements as the **baseline**. Note: "Role-type mode — using archetype: [id]."
3. If not found: synthesize typical requirements from training knowledge as the baseline. Note: "Role-type mode — archetype not in reference file, synthesized from training knowledge."
4. **Proceed to Step 1c (Market Research Synthesis)** before finalizing requirements.
5. Derive a `slug` from the role name (e.g., `agentic_ai_engineer`, `data_analyst`).

**Output of Phase 1:** A market-informed requirements list organized by category (hard_req / critical / preferred / cultural), with frequency annotations showing how many JDs mentioned each requirement.

### 1c. Market Research Synthesis (Role-Type Mode Only)

The archetype baseline reflects general expectations. Real market requirements shift constantly. This step grounds the gap analysis in current hiring reality.

**Step 1: Collect real JDs.**
Use web search to find 5-8 current job postings for the target role. Search queries:
- `"[role title]" jobs site:linkedin.com OR site:greenhouse.io OR site:lever.co`
- `"[role title]" hiring 2025 2026`
- If the user mentioned a target industry or company tier (e.g., "at FAANG", "at startups"), add that to the query.

Read at least 5 JDs. For each, extract:
- Hard requirements
- Preferred/nice-to-have skills
- Cultural signals
- Domain context and scale signals
- Compensation signals (if visible — helps gauge seniority calibration)

**Step 2: Frequency analysis.**
Tally how many JDs mention each requirement. Classify:
- **Universal** (4+ out of 5-8 JDs): These are true hard requirements for the market, even if one specific JD omits them.
- **Common** (2-3 JDs): Strong signal — should be in critical category.
- **Emerging** (1 JD, but represents a clear trend): Flag as forward-looking.
- **Outlier** (1 JD, company-specific): Deprioritize unless the user targets that specific company.

**Step 3: Merge with baseline.**
- Upgrade any archetype `preferred` requirement to `critical` if it appears as Universal in the market scan.
- Add any Universal or Common requirements not in the archetype at all.
- Add a `market_frequency` annotation to each requirement (e.g., "5/6 JDs").
- Flag any archetype `hard_req` that appears in 0-1 JDs as potentially outdated.
- Note emerging requirements separately — these are differentiators if the candidate can demonstrate them.

**Step 4: Synthesize market context.**
Write a brief (3-5 sentence) market context summary:
- What the market currently emphasizes for this role
- Any notable shifts from the archetype baseline
- Salary/seniority calibration if data is available
- Which companies are hiring most actively

This summary goes into the gap analysis YAML as `market_context`.

**Example output:**
```yaml
market_research:
  jds_analyzed: 6
  sources: ["LinkedIn", "Greenhouse", "Lever"]
  market_context: >
    The Agentic AI Engineer market in 2026 has shifted heavily toward production
    deployment and evaluation/observability. 5/6 JDs now list MCP or tool-use
    frameworks as hard requirements (up from preferred in 2025). RAG is table-stakes.
    Emerging: multi-modal agent systems and voice agent pipelines appearing in 2/6 JDs.
  frequency_adjustments:
    - requirement: "MCP"
      archetype_level: preferred
      market_level: hard_req
      frequency: "5/6"
    - requirement: "agent evaluation frameworks"
      archetype_level: null
      market_level: critical
      frequency: "4/6"
      note: "Not in archetype — new market requirement"
```

---

## Phase 2: Systematic Gap Analysis

For EVERY requirement extracted in Phase 1, assess the candidate's current standing.

### 2a. Evidence Search Protocol

For each requirement, check the career ledger in this order:
1. `skills_confirmed` — direct match → **COVERED**
2. `tools_confirmed` across all roles/projects — tool confirmed in real work → **COVERED**
3. `keywords_natural` arrays — keyword appears in achievements → **COVERED** (if multiple occurrences) or **PARTIAL** (if single/weak)
4. Achievement `action`/`method` fields — semantically related but keyword not present → **ADJACENT**
5. No match anywhere → **GAP**

### 2b. Coverage States

| State | Definition | Action |
|---|---|---|
| **COVERED** | Direct evidence in ledger: confirmed skill + real achievement demonstrating it | No action needed |
| **ADJACENT** | Related skill exists that can bridge to the requirement | Identify the bridge; plan a small project |
| **PARTIAL** | Weak or single evidence — exposure but not demonstrable depth | Strengthen with a focused artifact |
| **GAP** | No evidence at all | Requires active skill-building |

### 2c. Build the Gap Analysis Table

For each non-COVERED requirement, record:
```
requirement: [skill/tool/signal]
status: ADJACENT | PARTIAL | GAP
category: [see Phase 3 categories]
evidence: [what exists in ledger, or "none"]
bridge_from: [specific skill/project from ledger that connects]
```

**Coverage summary:**
```
covered: N  |  adjacent: N  |  partial: N  |  gap: N
coverage_rate: (covered + adjacent*0.5) / total_requirements
```

Fit assessment:
- ≥ 80%: Strong fit — plan focuses on polish and cultural signals
- 60-79%: Moderate fit — plan focuses on 2-3 key technical gaps + portfolio
- < 60%: Weak fit — flag this to the user; plan must be ambitious and realistic

---

## Phase 3: Gap Categorization & Prioritization

### 3a. Load Reference

Read `references/gap_categories.md` now. Use it to:
- Categorize each gap into one of 6 types
- Select the appropriate closing strategy
- Identify candidate-specific bridge actions from the bridge tables

### 3b. Categorize Each Gap

Assign every ADJACENT / PARTIAL / GAP item one category:
1. **Technical Skills** — missing tool, language, or framework
2. **Domain Knowledge** — missing industry/methodology expertise
3. **Portfolio Evidence** — has the skill but no public proof
4. **Credentials** — role expects a specific certification
5. **Cultural Signals** — open-source, writing, community presence
6. **Experience Depth** — exposure but not at required scale/seniority

### 3c. Prioritize Using Impact × Effort Matrix

For each gap, assess:
- **Impact** (high/low): Does closing this gap materially change the recruiter's perception?
  - High: hard_req gaps, gaps mentioned 3+ times in JD, cultural signals called out explicitly
  - Low: preferred/nice-to-have, one-time JD mentions
- **Effort** (high/low): How many hours realistically to close given existing skills?
  - Low: < 8 hours (adjacent skill, existing project can absorb it)
  - High: ≥ 8 hours (genuine new skill, requires sustained learning)

**Priority ordering:**
1. High-Impact / Low-Effort — do first (Week 1)
2. High-Impact / High-Effort — plan carefully (Weeks 2-3)
3. Low-Impact / Low-Effort — do if time allows (Week 4)
4. Low-Impact / High-Effort — skip; not worth the ROI during job search

---

## Phase 4: 30-Day Action Plan Generation

### 4a. Structure

Organize deliverables into 4 weeks:
- **Week 1:** Quick wins — Low-Effort gaps, portfolio publishing, free credentials
- **Week 2:** Core building — first High-Impact/High-Effort technical gap
- **Week 3:** Core building continued — second major gap, portfolio evidence
- **Week 4:** Polish — write-ups, community actions, resume bullet updates, application blitz

Each week has 2-4 deliverables. Do not overfill — a job seeker has 2-4 focused hours/day for gap-closing.

### 4b. Deliverable Template

For EVERY deliverable, write ALL of the following fields. Do not abbreviate or skip fields.

```
### [Week N] — [Deliverable Title]

**Gap closed:** [Which requirement this addresses]
**Why it matters:** [How this changes recruiter perception — be specific]
**Bridge from:** [The specific existing skill/project this builds on]

**How:**
1. [Specific step 1 — concrete enough to do without research]
2. [Specific step 2]
3. [Specific step 3]
   ...

**Time estimate:** [X hours]
**Deliverable:** [Exact artifact — e.g., "public GitHub repo", "blog post published at dev.to", "LinkedIn post", "PyPI package"]
**Resume bullet (add after completing):**
"[Draft XYZ-formula bullet: Accomplished X measured by Y by doing Z]"
```

### 4c. Hyper-Personalization Rules

These rules override everything. Apply without exception:

1. **Never recommend learning something already confirmed in the ledger.** Check `skills_confirmed` and `tools_confirmed` before recommending any skill.
2. **Every action must bridge FROM an existing skill or project.** Never say "start from scratch." Always name the specific existing project, achievement, or skill being extended.
3. **Every deliverable must produce a public, linkable artifact.** GitHub repo, published post, PyPI package, LinkedIn post, YouTube video — something with a URL.
4. **Leverage the existing GitHub repo first.** The resume-tailoring-engine is already public. New projects should extend it, reference it, or complement it.
5. **Time estimates must be realistic.** Assume 2-4 focused hours/day, not 8. Err conservative.
6. **Free over paid.** Only recommend paid certifications if the credential itself is the value signal.

### 4d. Special Case: Cultural Signals

If the JD or role archetype signals open-source contribution or technical writing:
- Name the specific repo to contribute to (one the candidate already uses)
- Name the type of contribution (documentation, test, bug fix, example)
- Name the specific writing prompt tied to their most impressive existing project
- Name the specific community to join (Discord, Slack, forum)

Do NOT give generic advice. Always name the specific target.

---

## Output

Write two files:

### File 1: `output/gap_plans/{slug}_gap_analysis.yaml`

```yaml
slug: [derived from target or role name]
mode: single_jd  # or role_type
target: "[Job title] at [Company]"  # or role archetype name
analyzed_at: "[YYYY-MM-DD]"

profile_snapshot:
  strongest_areas: [top 3-5 skill clusters from ledger]
  confirmed_skills_count: N
  total_achievements: N

# Role-type mode only — omit for single-JD mode
market_research:
  jds_analyzed: N
  sources: [list of platforms]
  market_context: "[3-5 sentence synthesis]"
  frequency_adjustments: []  # list of archetype overrides with frequency data

requirements_assessed: N
coverage_summary:
  covered: N
  adjacent: N
  partial: N
  gap: N
  coverage_rate: 0.XX
fit_level: strong | moderate | weak

gaps:
  - requirement: "[skill/signal]"
    status: GAP | ADJACENT | PARTIAL
    category: technical_skill | domain_knowledge | portfolio_evidence | credential | cultural_signal | experience_depth
    impact: high | low
    effort: high | low
    priority: 1 | 2 | 3 | skip
    bridge_from: "[existing skill/project from ledger]"
    closing_strategy: "[1-2 sentence specific action]"
    week: 1 | 2 | 3 | 4
```

### File 2: `output/gap_plans/{slug}_action_plan.md`

```markdown
# 30-Day Gap-Closing Plan: [Target Role]

**Analyzed:** [date] | **Fit level:** [strong/moderate/weak] | **Coverage:** [N]%
**Gaps to close:** [N total — N high-priority, N low-priority]

---

## Week 1: Quick Wins (~[N] hours total)
## Week 2: Core Building — [Theme] (~[N] hours total)
## Week 3: Core Building Continued — [Theme]
## Week 4: Polish & Proof

[Each week uses the deliverable template from 4b]

---

## Resume Updates After Week 4
## What to Skip (with rationale)
```

---

## Hard Constraints

1. Never fabricate metrics or claim skills not in the career ledger
2. Never recommend starting from scratch when an existing project can be extended
3. Every deliverable must be completable in 30 days alongside a job search
4. The plan must be specific enough that the user can start executing within the hour
5. If fit level is < 60%, flag this to the user BEFORE generating the plan and ask if they want to proceed
