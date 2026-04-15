# Underfill Recovery: Add Content Without Breaking Page Quality

Use this guide only after Phase 3 PDF verification fails the underfill gate in [SKILL.md](../SKILL.md): the resume is still 1 page, but `extracted_lines < 66`.

**Core rule:** Do not invent a new writing system for recovery. Reuse the main workflow:
- Use **Step 2.2** for what to expand or promote
- Use **Step 2.3** for how to write any added bullet
- Use **Step 2.4** and **Step 2.5** after expansion so the whole page stays internally consistent

## Constants

- `TARGET_FULL_LINES = 69`
- `MIN_PASS_LINES = 66`
- `empty_bottom_lines = TARGET_FULL_LINES - extracted_lines`

Pass only when `empty_bottom_lines <= 3`.

## Recovery By Rendered-Line Budget

Budget decisions are based on the rendered PDF gap, not raw bullet count. One bullet may consume 1 line or 3+ lines depending on wrap length.

### Tier 1: 4-6 Empty Bottom Lines

Target: add roughly `+3 to +5` rendered lines.

Allowed moves:
- Expand only within already selected items.
- Prefer adding one new bullet to the strongest selected supporting role that still has an unused, JD-relevant achievement under **Step 2.2**.
- If no supporting role qualifies, add one new bullet to the strongest selected project that still has an unused, JD-relevant achievement under **Step 2.2**.
- If the first addition is too short after regeneration, allow one more expansion only if it still fits the role/project ceilings in **Step 2.5** and remains truthful.

Do not promote a new experience in this tier unless every selected item is already maximally and truthfully expanded.

### Tier 2: 7-10 Empty Bottom Lines

Target: add roughly `+6 to +9` rendered lines.

Allowed moves:
- First check whether expanding existing selected items can fill the gap cleanly under the same **Step 2.2** ceilings and relevance rules.
- If not, promote one new role or project from HOLD/MAYBE using **Step 2.1** shortlist logic and **Step 2.2** include-first logic.
- Promotion is preferred over stuffing multiple weak bullets into already selected items.

### Tier 3: 11+ Empty Bottom Lines

Target: add `+10+` rendered lines.

Allowed moves:
- Promote one new truthful role or project first.
- Then expand selected items within their normal ceilings if more space still remains after regeneration.

In this tier, adding only one extra bullet is usually not enough.

## Selection Order For Expansion

When multiple candidates are available, use this order:

1. Strongest selected supporting role with unused relevant achievements
2. Strongest selected project with unused relevant achievements
3. Strongest HOLD/MAYBE item eligible under **Step 2.1** + **Step 2.2**
4. Stop only when no truthful, JD-relevant addition remains

Apply the same relevance, metric, and project-protection reasoning already defined in **Step 2.2**:
- prefer achievements with direct JD overlap
- prefer quantified achievements when possible
- compare a new project against the weakest selected role before promoting it

Do not promote a new experience if it is weaker than a valid expansion inside the current selected set for that line budget.

## Writing Any Added Bullet

Every added bullet must reuse **Step 2.3** exactly:
- choose an unused achievement selected under **Step 2.2**
- begin with a strong past-tense action verb
- use the XYZ structure
- front-load metrics when truthful
- mirror JD verbs and noun phrases
- respect clause-load limits
- respect `reframe_ceiling` or the plausibility test

The added bullet must read like it belongs on the same page as the original bullets. It should not suddenly become much longer, more generic, or more keyword-stuffed than the rest of the resume.

## After Adding Content

After every recovery pass:

1. Re-run **Step 2.4** if the new bullet changes what the summary or skills should emphasize
2. Re-run **Step 2.5** so action verbs, keyword placement, bullet ceilings, and page rhythm stay consistent
3. Regenerate the PDF
4. Re-check `pages`, `extracted_lines`, and `empty_bottom_lines`

Repeat until the resume passes (`empty_bottom_lines <= 3`) or no truthful addition remains.

## Warnings

- Do not add filler bullets just to consume space.
- Do not promote a weak new experience when a better expansion exists in the selected set.
- Do not exceed the normal role/project ceilings from **Step 2.5** unless there is no other truthful way to satisfy the page-fill requirement.
- If the next possible addition would materially reduce relevance or force fabrication, stop and report the remaining underfill honestly.
