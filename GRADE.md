---
name: resume_quality_grader
description: "Evaluates a generated resume against the quality rubric. Scores 4 judgment-requiring dimensions that automated scripts cannot assess: XYZ formula adherence, keyword contextual placement, summary quality, and reframing integrity. Run the automated grader first (scripts/grade_resume.py), then follow this file to complete the evaluation."
---

# Resume Quality Grader

## Quick Start

1. **Read this entire file first.** Do not start grading until you understand all dimensions.
2. **Run the automated grader** to get script-scored dimensions:
   ```bash
   python3 scripts/grade_resume.py output/scripts/generate_{slug}_resume.js output/keywords/jd_keywords_{slug}.yaml
   ```
3. **Read the partial grade** at `output/grades/{slug}_grade.yaml`.
4. **Read the inputs** listed below.
5. **Evaluate** the 4 agent-scored dimensions following the rubric in this file.
6. **Write the final grade** by updating the YAML with your scores.

## Required Inputs

| Input | Path | Purpose |
|---|---|---|
| Partial grade | `output/grades/{slug}_grade.yaml` | Script-scored dimensions to complete |
| Generated script | `output/scripts/generate_{slug}_resume.js` | Resume content (bullets, summary, skills) |
| Keyword YAML | `output/keywords/jd_keywords_{slug}.yaml` | Keyword placement data |
| Career ledger | `career_ledger.yaml` | Source of truth for reframing checks |
| Grading rubric | `references/grading_rubric.yaml` | Dimension definitions and weights |

---

## Dimension 1: XYZ Formula Adherence (Weight: 15)

**What to evaluate:** Does each bullet follow the XYZ formula — Accomplished [X] as measured by [Y], by doing [Z]?

### Scoring Criteria

For each bullet, assess three components:

| Component | What to look for | Points |
|---|---|---|
| **[X] Achievement** | Starts with action verb, states a clear positive outcome | 0-1 |
| **[Y] Measurement** | Contains a specific metric, percentage, scale, or quantified result | 0-1 |
| **[Z] Method** | Describes the tools, techniques, or approach used | 0-1 |

**Per-bullet score:** Sum of component points (0-3).

**Dimension score calculation:**
```
total_points = sum of all bullet scores
max_points = total_bullets * 3
xyz_score = (total_points / max_points) * 100
```

### Red Flags (deduct 5 points each)

- Bullet describes a task without an outcome ("Managed daily reports")
- Bullet uses passive voice ("Reports were generated")
- Bullet front-loads the method instead of the achievement ("Using Python, created a script...")
- Bullet has a metric that is disconnected from the action ("Built a pipeline. Saved $2M annually.")

### Examples

**Good (3/3):** "Built a predictive model that reduced customer churn by 15% using random forest algorithms on 100K+ records."
- X: Built a predictive model that reduced customer churn ✓
- Y: by 15%, on 100K+ records ✓
- Z: using random forest algorithms ✓

**Partial (2/3):** "Developed a data pipeline to process and normalize pricing data from 6 major grocery platforms."
- X: Developed a data pipeline ✓
- Y: (no metric) ✗
- Z: process and normalize pricing data from 6 platforms ✓

**Weak (1/3):** "Handled customer queries via live chat and resolved complaints."
- X: (no clear achievement) ✗
- Y: (no metric) ✗
- Z: via live chat ✓

---

## Dimension 2: Keyword Contextual Placement (Weight: 10)

**What to evaluate:** Are keywords woven naturally into achievement sentences, or stuffed awkwardly?

### Scoring Criteria

Read every keyword from the keyword YAML that has `status: PLACED`. For each, find where it appears in the resume content and assess:

| Quality | Description | Points per keyword |
|---|---|---|
| **Contextual** | Keyword is part of an achievement statement with a business outcome | 2 |
| **Acceptable** | Keyword appears in a method/tool description within a bullet | 1 |
| **Stuffed** | Keyword appears in a standalone list, is forced into unrelated context, or reads unnaturally | 0 |

**Skills section exception:** Keywords in the Skills line are acceptable (that's a standard resume section). Only score keywords in bullets and summary.

**Acronym check:** For each technical acronym, verify the full form appears at least once. Deduct 2 points per acronym without expansion.

**Dimension score calculation:**
```
keyword_points = sum of per-keyword scores (for bullets/summary only)
max_keyword_points = placed_keywords_in_bullets * 2
contextual_score = (keyword_points / max_keyword_points) * 100
```

### Red Flags (deduct 10 points each)

- Same keyword repeated 4+ times across bullets (beyond skills section)
- A bullet reads like a keyword list disguised as a sentence
- Keywords from completely different domains forced into one bullet

---

## Dimension 3: Summary Quality (Weight: 5)

**What to evaluate:** Does the professional summary effectively anchor the candidate to the target role?

### Scoring Criteria (0-100)

| Criterion | Points | How to assess |
|---|---|---|
| **JD title anchored** | 30 | Summary contains the exact job title from the JD (or a very close variant). Check the title in the `title` field of the first workExperience entry or the keyword YAML context. |
| **Metric-driven** | 25 | Summary contains at least one quantified claim (number, percentage, scale). |
| **Role-relevant framing** | 25 | Summary emphasizes skills/experience most relevant to THIS specific JD, not generic background. |
| **Concise and impactful** | 10 | No filler words, no soft skills claims ("strong communicator"), no buzzword chains. |
| **No prohibited content** | 10 | No soft skills (leadership, teamwork, communication) unless they're part of a quantified achievement. No first-person pronouns. |

### Example Assessment

**Strong (90/100):**
> "AI Engineer with hands-on experience building multi-agent workflows, Python ETL pipelines, and API integrations. Shipped production systems serving 200+ users with 20% retention improvement."
- Title anchored: "AI Engineer" matches JD ✓ (30)
- Metric-driven: "200+ users", "20% retention improvement" ✓ (25)
- Role-relevant: multi-agent, ETL, API — all JD-relevant ✓ (25)
- Concise: 29 words, no filler ✓ (10)
- No prohibited: clean ✗ slight buzzword density (-5)

---

## Dimension 4: Reframing Integrity (Weight: 5)

**What to evaluate:** Does each bullet stay within the `reframe_ceiling` defined in `career_ledger.yaml`?

### Process

1. Read `career_ledger.yaml` to get each role's `plausibility_ceiling` and each achievement's `reframe_ceiling`.
2. For each bullet in the resume, identify which career ledger achievement(s) it draws from (match by role/company and content).
3. Check the bullet against the ceiling.

### Scoring Criteria

| Violation | Deduction |
|---|---|
| Bullet claims a responsibility explicitly excluded by `reframe_ceiling` | -20 per violation |
| Bullet inflates a metric beyond what the ledger records | -15 per violation |
| Bullet claims sole credit when ceiling says "partnered with" or "part of team" | -10 per violation |
| Bullet claims a title or seniority not in the ledger | -20 per violation |
| Achievement cannot be traced to any ledger entry | -25 per violation |

**Dimension score:** Start at 100, apply deductions, cap at 0.

### What Is NOT a Violation

- Rewording an achievement for clarity or impact (as long as meaning is preserved)
- Combining two achievements from the same role into one bullet (if both are from the ledger)
- Using different keywords than the ledger's `keywords_natural` (that's the whole point of tailoring)
- Omitting part of an achievement to fit space constraints

---

## Final Score Calculation

After scoring all 4 agent dimensions, compute the overall weighted score:

```
overall_score = (
    bullet_structure_score * 0.05 +
    bullet_length_score * 0.05 +      # Note: bullet_structure from rubric is split
    metric_density_score * 0.15 +
    keyword_coverage_score * 0.15 +
    verb_quality_score * 0.10 +
    summary_length_score * 0.05 +      # Script-scored part of summary
    xyz_formula_score * 0.15 +
    keyword_contextual_score * 0.10 +
    summary_quality_score * 0.05 +     # Agent-scored part of summary
    reframing_integrity_score * 0.05 +
    one_page_fit_score * 0.05 +        # From script if available
    ats_compliance_score * 0.05        # From script if available
)
```

**Note:** If `one_page_fit` and `ats_compliance` are not scored by the script (they require PDF verification), omit them and redistribute their weight proportionally.

**Simplified formula (without PDF checks):**
```
overall_score = (
    bullet_structure * 0.056 +
    bullet_length * 0.056 +
    metric_density * 0.167 +
    keyword_coverage * 0.167 +
    verb_quality * 0.111 +
    summary_length * 0.056 +
    xyz_formula * 0.167 +
    keyword_contextual * 0.111 +
    summary_quality * 0.056 +
    reframing_integrity * 0.056
)
```

## Output

Update the grade YAML at `output/grades/{slug}_grade.yaml`:

1. Fill in the 4 `null` agent-scored dimensions with your scores and details.
2. Calculate and fill in `overall_score`.
3. Add a `grading_notes` field with 2-3 sentence summary of quality findings.
4. Add a `top_improvements` list with the 1-3 highest-impact changes that would improve the score.

### Example completed agent dimensions:

```yaml
  xyz_formula:
    score: 82
    per_bullet_scores:
      - bullet: "Built and deployed a multi-agent chatbot..."
        x: 1
        y: 0
        z: 1
        notes: "Strong action and method, but no quantified outcome"
    red_flags: []

  keyword_contextual_placement:
    score: 88
    contextual_count: 8
    acceptable_count: 3
    stuffed_count: 0
    acronym_violations: []

  summary_quality:
    score: 90
    jd_title_match: true
    has_metric: true
    role_relevant: true
    prohibited_content: []

  reframing_integrity:
    score: 95
    violations: []
    notes: "All bullets traceable to ledger achievements. No ceiling breaches."

overall_score: 87
grading_notes: "Strong keyword coverage and metric density. XYZ structure could improve — 3 bullets lack quantified outcomes. Summary effectively anchors the target role."
top_improvements:
  - "Add metrics to bullets for NuOnc roles 1 and 4 (currently unquantified)"
  - "Expand 'LLM' acronym on first use in bullets"
```
