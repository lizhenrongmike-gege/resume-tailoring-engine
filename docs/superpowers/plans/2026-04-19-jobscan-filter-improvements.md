# JobScan Filter Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut filter noise from a Tier-1 ATS scan (currently 47 survivors out of 1,436 raw, with most survivors irrelevant) by adding a positive title allow-list, broadening the seniority/excluded-title blocklists, populating + filtering on department, and fixing stale ATS slugs.

**Architecture:** All changes live inside the existing `jobscan/` Python package. The hard filter pipeline in `jobscan/filters.py` gets two new gates (positive title keyword, department exclusion). `RawPosting` gains a `department` field that all three ATS connectors populate from data they already fetch. Slug fixes are config-only.

**Tech Stack:** Python 3.11+, `requests`, `pytest` with `unittest.mock` (existing test patterns mock `requests.get`/`post`).

---

## Baseline (before changes)

Run `python3 jobscan/scan.py --tier1 --no-rank --days 14`:
- Raw: **1,436** postings
- Distinct after intra-run dedup: **1,135**
- Pass hard filter: **47** (with ~7 actually relevant to user's lanes)
- Errors: Deel (Greenhouse 404 — slug stale), Clay (Ashby 401 — board private)

Goal after this plan: ≤15 survivors, ≥6 of the 7 known-relevant roles still present.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `jobscan/config.py` | Lane defs, regex patterns, blocklists | Extend SENIORITY_PATTERN + EXCLUDED_TITLES; load POSITIVE_TITLE_KEYWORDS + EXCLUDED_DEPARTMENT_KEYWORDS from YAML; fix Deel slug, mark Clay disabled |
| `jobscan/filter_keywords.yaml` | User-editable positive titles + excluded departments | NEW — organized by lane so the user can tune without touching Python |
| `jobscan/connectors/base.py` | `RawPosting` dataclass | Add `department: str = ""` field |
| `jobscan/connectors/greenhouse.py` | Greenhouse parser | Populate `department` from `departments[].name` |
| `jobscan/connectors/ashby.py` | Ashby parser | Populate `department` from `department`; add `?includeCompensation=true` |
| `jobscan/connectors/lever.py` | Lever parser | Populate `department` from `categories.team`/`categories.department` |
| `jobscan/filters.py` | Hard filter pipeline | Add positive-title gate + department gate |
| `tests/test_filters.py` | Filter tests | New tests for new gates and extended seniority/excluded-title patterns |
| `tests/test_greenhouse.py` / `test_ashby.py` / `test_lever.py` | Connector tests | Add sample data + assertions for `department` |

---

## Task 1: Extend seniority pattern + excluded titles

**Files:**
- Modify: `jobscan/config.py:114` (SENIORITY_PATTERN)
- Modify: `jobscan/config.py:118-161` (EXCLUDED_TITLES)
- Modify: `tests/test_filters.py` (add tests)

- [ ] **Step 1: Write failing tests for new exclusions**

Append to `tests/test_filters.py`:

```python
def test_chief_and_officer_titles_filtered():
    postings = [
        _posting(title="Chief Audit Officer"),
        _posting(title="Chief Risk Officer"),
        _posting(title="Head of Compliance"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 0
    assert all("seniority" in r.lower() for r in result.reasons.values())


def test_extended_excluded_titles_filtered():
    postings = [
        _posting(title="AV Engineer"),
        _posting(title="IT Engineer"),
        _posting(title="Data Center Engineer II"),
        _posting(title="Design Engineer, Presence"),
        _posting(title="Android Engineer, Terminal"),
        _posting(title="iOS Engineer"),
        _posting(title="Research Engineer – Training Infra"),
        _posting(title="Account Executive, Funded Startups"),
        _posting(title="Sales Development Representative"),
        _posting(title="Customer Support Specialist"),
        _posting(title="Accountant"),
        _posting(title="Communications Manager"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 0
```

- [ ] **Step 2: Run tests — verify they FAIL**

Run: `pytest tests/test_filters.py::test_chief_and_officer_titles_filtered tests/test_filters.py::test_extended_excluded_titles_filtered -v`
Expected: both FAIL (titles currently pass through).

- [ ] **Step 3: Extend SENIORITY_PATTERN in `jobscan/config.py`**

Replace line 114:

```python
SENIORITY_PATTERN = (
    r"\b(?:Senior|Sr\.?|Staff|Principal|Lead|Manager|Director|VP|"
    r"Head\s+of|Chief\s+\w+\s+Officer|Chief)\b"
)
```

- [ ] **Step 4: Extend EXCLUDED_TITLES in `jobscan/config.py`**

Add these entries inside the existing `EXCLUDED_TITLES` list (preserve existing entries, append before the closing `]`):

```python
    "AV Engineer",
    "IT Engineer",
    "Data Center Engineer",
    "Design Engineer",
    "Android Engineer",
    "iOS Engineer",
    "Mobile Engineer",
    "Research Engineer",
    "Account Executive",
    "Sales Development Representative",
    "SDR",
    "Business Development Representative",
    "BDR",
    "Customer Support",
    "Support Specialist",
    "Accountant",
    "Communications",
    "Comms",
    "Creative Technologist",
    "Production Support Engineer",
```

- [ ] **Step 5: Run new tests — verify they PASS**

Run: `pytest tests/test_filters.py -v`
Expected: all tests pass (existing + 2 new).

- [ ] **Step 6: Commit**

```bash
git add jobscan/config.py tests/test_filters.py
git commit -m "feat(jobscan): broaden seniority and excluded-title filters"
```

---

## Task 2: Add positive title keyword filter (YAML-backed)

**Design intent:** The positive title list is the user's primary tuning knob. It must be editable without touching Python. We externalize it to `jobscan/filter_keywords.yaml`, organized by lane with comments. `config.py` reads the file at import time and exposes a flat `POSITIVE_TITLE_KEYWORDS` list to the filter.

**Files:**
- Create: `jobscan/filter_keywords.yaml`
- Modify: `jobscan/config.py` (load YAML, expose flat list)
- Modify: `jobscan/filters.py` (add positive check)
- Modify: `tests/test_filters.py` (tests)
- Modify: `tests/test_config.py` (test YAML load + flatten)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_filters.py`:

```python
def test_positive_keyword_required():
    # Title with no positive keyword and no obvious exclusion — should fail
    result = apply_hard_filters([
        _posting(title="Reserve Operations Deputy"),
    ])
    assert len(result.passed) == 0
    assert "positive" in list(result.reasons.values())[0].lower()


def test_positive_keyword_match_passes():
    # "Fraud Analyst" is the default fixture — already a positive match
    postings = [
        _posting(title="Risk Operations Analyst"),
        _posting(title="Trust & Safety Analyst"),
        _posting(title="GTM Engineer"),
        _posting(title="Implementation Engineer"),
        _posting(title="Solutions Engineer"),
        _posting(title="KYC Analyst"),
        _posting(title="Compliance Analyst"),
        _posting(title="Data Analyst"),
        _posting(title="Business Operations Analyst"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == len(postings), [r for r in result.reasons.values()]
```

Append to `tests/test_config.py`:

```python
def test_positive_title_keywords_loaded_and_flat():
    from jobscan.config import POSITIVE_TITLE_KEYWORDS
    assert isinstance(POSITIVE_TITLE_KEYWORDS, list)
    assert all(isinstance(k, str) for k in POSITIVE_TITLE_KEYWORDS)
    # Sanity: a few known entries from each lane present
    expected = {"Fraud", "Data Analyst", "Solutions Engineer", "GTM"}
    assert expected.issubset(set(POSITIVE_TITLE_KEYWORDS))
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `pytest tests/test_filters.py::test_positive_keyword_required tests/test_config.py::test_positive_title_keywords_loaded_and_flat -v`
Expected: both FAIL.

- [ ] **Step 3: Create `jobscan/filter_keywords.yaml`**

Create new file with this exact content:

```yaml
# Filter keywords for jobscan hard filter.
# Edit freely — changes take effect on the next scan run.
#
# positive_title_keywords:
#   For a job to pass, its title must contain (case-insensitive substring)
#   at least ONE of these keywords. Organized by lane for readability;
#   the loader flattens all lanes into a single list.
#
# excluded_department_keywords:
#   A job is rejected if its `department` field contains (case-insensitive
#   substring) any of these. Used to drop sales/marketing/infra roles even
#   when the title would otherwise pass.

positive_title_keywords:
  lane_1_risk_fraud_payments_onboarding_ops:
    - Risk
    - Fraud
    - Trust & Safety
    - Trust and Safety
    - KYC
    - AML
    - Compliance
    - Disputes
    - Identity
    - Onboarding
    - Merchant

  lane_2_operations_data_analyst:
    - Data Analyst
    - Operations Analyst
    - Ops Analyst
    - Business Analyst
    - Business Operations
    - Business Operations Analyst
    - Strategy and Operations
    - Strategy & Operations

  lane_3_ai_implementation_solutions:
    - Implementation Engineer
    - Implementation Consultant
    - Solutions Engineer
    - Technical Success
    - Customer Success Engineer
    - Technical Operations
    - Deployment Engineer
    - Onboarding Engineer
    - Professional Services Engineer
    - AI Solutions

  lane_4_gtm:
    - GTM
    - Revenue Operations
    - RevOps
    - Marketing Technologist
    - Growth Engineer
    - Sales Engineering

  generic_applied_ai:
    # Pure AI Engineer roles still gated by customer-signal check in filters.py
    - AI Engineer
    - ML Engineer
    - LLM Engineer
    - Applied AI

excluded_department_keywords:
  - Sales
  - Account Executive
  - Marketing
  - Communications
  - Public Relations
  - Recruiting
  - People
  - Human Resources
  - Finance
  - Accounting
  - Legal
  - Infrastructure
  - Platform Engineering
  - Mobile Engineering
  - Hardware
  - Research Science
  - Design
  - Brand
```

- [ ] **Step 4: Update `jobscan/config.py` to load YAML**

Add to the top of `jobscan/config.py` (after the existing `import re`):

```python
from pathlib import Path

import yaml

_FILTER_KEYWORDS_PATH = Path(__file__).parent / "filter_keywords.yaml"


def _load_filter_keywords() -> dict:
    with open(_FILTER_KEYWORDS_PATH, "r") as f:
        return yaml.safe_load(f)


_filter_keywords = _load_filter_keywords()

# Flatten lane-grouped positive keywords into one list for the filter.
POSITIVE_TITLE_KEYWORDS: list[str] = [
    keyword
    for lane_keywords in _filter_keywords["positive_title_keywords"].values()
    for keyword in lane_keywords
]

EXCLUDED_DEPARTMENT_KEYWORDS: list[str] = list(
    _filter_keywords["excluded_department_keywords"]
)
```

(The `EXCLUDED_DEPARTMENT_KEYWORDS` export is consumed by Task 4 — defining it here keeps both knobs in one place.)

- [ ] **Step 5: Add positive check to `jobscan/filters.py`**

Update the import block at the top:

```python
from jobscan.config import (
    SENIORITY_PATTERN, YOE_PATTERN, EXCLUDED_TITLES, LOCATION_ALLOW_PATTERN,
    POSITIVE_TITLE_KEYWORDS,
)
```

Insert at the **start** of `_check_posting()`, before the seniority check:

```python
    title_lower = title.lower()
    if not any(kw.lower() in title_lower for kw in POSITIVE_TITLE_KEYWORDS):
        return "No positive title keyword match"
```

- [ ] **Step 6: Run all filter + config tests — verify PASS**

Run: `pytest tests/test_filters.py tests/test_config.py -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add jobscan/filter_keywords.yaml jobscan/config.py jobscan/filters.py tests/test_filters.py tests/test_config.py
git commit -m "feat(jobscan): add YAML-backed positive title keyword filter"
```

---

## Task 3: Add `department` field to `RawPosting` and populate in connectors

**Files:**
- Modify: `jobscan/connectors/base.py` (add field)
- Modify: `jobscan/connectors/greenhouse.py` (populate)
- Modify: `jobscan/connectors/ashby.py` (populate + add comp query param)
- Modify: `jobscan/connectors/lever.py` (populate)
- Modify: `tests/test_greenhouse.py`, `tests/test_ashby.py`, `tests/test_lever.py`

- [ ] **Step 1: Write failing test for `RawPosting.department`**

Append to `tests/test_connectors_base.py`:

```python
def test_raw_posting_has_department_default():
    from jobscan.connectors.base import RawPosting
    p = RawPosting(
        title="X", company="Y", location="Z",
        description="", url="", posted_date=None, source="test",
    )
    assert p.department == ""


def test_raw_posting_accepts_department():
    from jobscan.connectors.base import RawPosting
    p = RawPosting(
        title="X", company="Y", location="Z",
        description="", url="", posted_date=None, source="test",
        department="Risk",
    )
    assert p.department == "Risk"
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `pytest tests/test_connectors_base.py -v`
Expected: FAIL (no `department` field).

- [ ] **Step 3: Add `department` field to `RawPosting`**

In `jobscan/connectors/base.py`, replace the dataclass:

```python
@dataclass
class RawPosting:
    """A job posting as returned by any connector."""
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: str | None
    source: str
    department: str = ""
```

- [ ] **Step 4: Run test — verify PASS**

Run: `pytest tests/test_connectors_base.py -v`
Expected: PASS.

- [ ] **Step 5: Write failing tests for connector `department` extraction**

Update `tests/test_greenhouse.py` — change the first job entry in `SAMPLE_GREENHOUSE_RESPONSE` to include departments:

```python
        {
            "title": "Fraud Analyst",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
            "content": "<p>Investigate fraud patterns using SQL...</p>",
            "updated_at": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S-05:00"),
            "departments": [{"id": 1, "name": "Risk"}],
        },
```

Add a new test in the same file:

```python
@patch("jobscan.connectors.greenhouse.requests.get")
def test_department_extracted(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GREENHOUSE_RESPONSE
    mock_get.return_value = mock_resp
    conn = GreenhouseConnector()
    results = conn.fetch_company("stripe", "Stripe", days_back=7)
    assert results[0].department == "Risk"
```

Append the equivalent test in `tests/test_ashby.py` (use this sample data; mirror the existing `@patch("jobscan.connectors.ashby.requests.post")` pattern in that file):

```python
SAMPLE_ASHBY_WITH_DEPT = {
    "jobs": [
        {
            "title": "Compliance Analyst",
            "location": "San Francisco, CA",
            "jobUrl": "https://jobs.ashbyhq.com/decagon/abc",
            "descriptionPlain": "Compliance work.",
            "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "department": "Legal & Compliance",
        }
    ]
}

@patch("jobscan.connectors.ashby.requests.post")
def test_department_extracted_ashby(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_ASHBY_WITH_DEPT
    mock_post.return_value = mock_resp
    from jobscan.connectors.ashby import AshbyConnector
    results = AshbyConnector().fetch_company("decagon", "Decagon", days_back=7)
    assert results[0].department == "Legal & Compliance"
```

Append in `tests/test_lever.py` (mirror the existing `@patch("jobscan.connectors.lever.requests.get")` pattern):

```python
SAMPLE_LEVER_WITH_DEPT = [
    {
        "text": "KYC Analyst",
        "categories": {
            "location": "Remote",
            "team": "Risk",
            "department": "Operations",
        },
        "hostedUrl": "https://jobs.lever.co/plaid/xyz",
        "descriptionPlain": "KYC work.",
        "createdAt": int((datetime.now() - timedelta(days=1)).timestamp() * 1000),
    }
]

@patch("jobscan.connectors.lever.requests.get")
def test_department_extracted_lever(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_LEVER_WITH_DEPT
    mock_get.return_value = mock_resp
    from jobscan.connectors.lever import LeverConnector
    results = LeverConnector().fetch_company("plaid", "Plaid", days_back=7)
    # Lever: prefer team, fall back to department
    assert results[0].department == "Risk"
```

- [ ] **Step 6: Run tests — verify FAIL**

Run: `pytest tests/test_greenhouse.py tests/test_ashby.py tests/test_lever.py -v`
Expected: 3 new tests FAIL (department always empty).

- [ ] **Step 7: Populate `department` in `jobscan/connectors/greenhouse.py`**

In `GreenhouseConnector.fetch_company`, change the `RawPosting(...)` call to include:

```python
            depts = job.get("departments") or []
            dept = ", ".join(d.get("name", "") for d in depts if d.get("name"))

            results.append(RawPosting(
                title=job.get("title", ""),
                company=company_name,
                location=job.get("location", {}).get("name", ""),
                description=_strip_html(job.get("content", "")),
                url=job.get("absolute_url", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="greenhouse",
                department=dept,
            ))
```

- [ ] **Step 8: Populate `department` in `jobscan/connectors/ashby.py` + add comp param**

Change the BASE_URL line:

```python
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
```

Change the `RawPosting(...)` call to include:

```python
            results.append(RawPosting(
                title=job.get("title", ""),
                company=company_name,
                location=job.get("location", ""),
                description=job.get("descriptionPlain", ""),
                url=job.get("jobUrl", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="ashby",
                department=job.get("department", "") or "",
            ))
```

- [ ] **Step 9: Populate `department` in `jobscan/connectors/lever.py`**

Change the `RawPosting(...)` call to include (prefer `team`, fall back to `department`):

```python
            categories = posting.get("categories", {})
            dept = categories.get("team") or categories.get("department") or ""
            results.append(RawPosting(
                title=posting.get("text", ""),
                company=company_name,
                location=categories.get("location", ""),
                description=posting.get("descriptionPlain", ""),
                url=posting.get("hostedUrl", ""),
                posted_date=posted.strftime("%Y-%m-%d"),
                source="lever",
                department=dept,
            ))
```

- [ ] **Step 10: Run all connector tests — verify PASS**

Run: `pytest tests/test_greenhouse.py tests/test_ashby.py tests/test_lever.py tests/test_connectors_base.py -v`
Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add jobscan/connectors/ tests/test_connectors_base.py tests/test_greenhouse.py tests/test_ashby.py tests/test_lever.py
git commit -m "feat(jobscan): extract department from Greenhouse/Ashby/Lever connectors"
```

---

## Task 4: Add department exclusion filter (YAML-backed)

**Design intent:** `EXCLUDED_DEPARTMENT_KEYWORDS` was already defined in Task 2 by loading from `jobscan/filter_keywords.yaml`. This task only wires it into the filter pipeline. The user can edit the YAML to add/remove excluded departments without touching Python.

**Files:**
- Modify: `jobscan/filters.py` (add department check)
- Modify: `tests/test_filters.py` (tests)
- Modify: `tests/test_config.py` (test YAML load for excluded_department_keywords)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_filters.py`:

```python
def test_excluded_department_filter():
    postings = [
        _posting(title="Data Analyst",
                 department="Sales - Account Executives (NA)"),
        _posting(title="Operations Analyst",
                 department="Engineering - Infrastructure"),
        _posting(title="Risk Analyst",
                 department="Marketing"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 0
    assert all("department" in r.lower() for r in result.reasons.values())


def test_allowed_department_passes():
    postings = [
        _posting(title="Data Analyst", department="Risk"),
        _posting(title="Operations Analyst",
                 department="Trust & Safety"),
    ]
    result = apply_hard_filters(postings)
    assert len(result.passed) == 2
```

Append to `tests/test_config.py`:

```python
def test_excluded_department_keywords_loaded():
    from jobscan.config import EXCLUDED_DEPARTMENT_KEYWORDS
    assert isinstance(EXCLUDED_DEPARTMENT_KEYWORDS, list)
    assert all(isinstance(d, str) for d in EXCLUDED_DEPARTMENT_KEYWORDS)
    expected = {"Sales", "Marketing", "Infrastructure"}
    assert expected.issubset(set(EXCLUDED_DEPARTMENT_KEYWORDS))
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `pytest tests/test_filters.py::test_excluded_department_filter -v`
Expected: FAIL (no department check yet). The config test should already PASS from Task 2 — that's fine, it's a regression guard.

- [ ] **Step 3: Add department check to `jobscan/filters.py`**

Update the import block to include `EXCLUDED_DEPARTMENT_KEYWORDS`:

```python
from jobscan.config import (
    SENIORITY_PATTERN, YOE_PATTERN, EXCLUDED_TITLES, LOCATION_ALLOW_PATTERN,
    POSITIVE_TITLE_KEYWORDS, EXCLUDED_DEPARTMENT_KEYWORDS,
)
```

Insert after the excluded-title loop and before the AI Engineer check:

```python
    if posting.department:
        dept_lower = posting.department.lower()
        for excluded in EXCLUDED_DEPARTMENT_KEYWORDS:
            if excluded.lower() in dept_lower:
                return f"Excluded department: {posting.department}"
```

- [ ] **Step 4: Run all filter + config tests — verify PASS**

Run: `pytest tests/test_filters.py tests/test_config.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add jobscan/filters.py tests/test_filters.py tests/test_config.py
git commit -m "feat(jobscan): wire YAML-backed department exclusion into filter"
```

---

## Task 5: Fix stale ATS slugs

**Files:**
- Modify: `jobscan/config.py` (PRIORITY_COMPANIES entries for Deel and Clay)

- [ ] **Step 1: Verify current Deel/Clay slug status**

Run:
```bash
python3 -c "
import requests
for slug in ['deel', 'deelhq', 'deelinc']:
    r = requests.get(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs', timeout=10)
    print('GH', slug, r.status_code)
for slug in ['deel', 'deelhq']:
    r = requests.get(f'https://api.lever.co/v0/postings/{slug}', timeout=10)
    print('Lever', slug, r.status_code, len(r.json()) if r.status_code==200 else '')
for slug in ['deel', 'deelhq']:
    r = requests.post(f'https://api.ashbyhq.com/posting-api/job-board/{slug}', json={}, timeout=10)
    print('Ashby', slug, r.status_code)
"
```

Record which slug returns 200. If none do, run the existing discovery script:

```bash
python3 jobscan/discover_slugs.py 2>&1 | grep -i "deel\|clay"
```

- [ ] **Step 2: Update `PRIORITY_COMPANIES` in `jobscan/config.py`**

For each fixed slug found in Step 1, replace the corresponding entry. If no public board exists for a company (Clay's Ashby board returns 401 — private), mark it disabled by adding `"enabled": False`:

Example replacements:

```python
    # Replace if Step 1 found a working Deel slug (e.g. 'deelhq'):
    {"name": "Deel", "ats": "greenhouse", "slug": "deelhq"},

    # Clay's Ashby board is private — disable until a public source is found:
    {"name": "Clay", "ats": "ashby", "slug": "clay", "enabled": False},
```

- [ ] **Step 3: Update `run_tier1` in `jobscan/scan.py` to honor `enabled`**

In `jobscan/scan.py:77`, change:

```python
    for company in PRIORITY_COMPANIES:
        ats = company["ats"]
        if ats not in _CONNECTORS:
```

to:

```python
    for company in PRIORITY_COMPANIES:
        if company.get("enabled", True) is False:
            continue
        ats = company["ats"]
        if ats not in _CONNECTORS:
```

- [ ] **Step 4: Re-run scan, confirm no 404/401 errors for Deel/Clay**

Run: `python3 jobscan/scan.py --tier1 --no-rank --days 14 2>&1 | grep -E "(WARNING|ERROR)"`
Expected: no Deel 404, no Clay 401.

- [ ] **Step 5: Commit**

```bash
git add jobscan/config.py jobscan/scan.py
git commit -m "fix(jobscan): correct stale ATS slugs and add enabled flag"
```

---

## Task 6: Verification — re-run scan and document delta

**Files:** none (validation only)

- [ ] **Step 1: Re-run the scan**

Run: `python3 jobscan/scan.py --tier1 --no-rank --days 14 2>&1 | tee /tmp/scan-after.txt | tail -80`

- [ ] **Step 2: Compare survivor count vs. baseline**

Baseline (pre-plan): 1,436 raw → 47 survivors.

Record post-plan numbers from `/tmp/scan-after.txt`:
- Raw postings:
- After hard filter:
- Of survivors, how many of the 7 known-relevant baseline roles are still present?

Known-relevant baseline roles to check:
1. Plaid — Consumer Compliance Analyst
2. Chime — Analyst, Identity & KYC
3. Instacart — Fraud & Identity Specialist (Contract)
4. Affirm — Analyst II, Strategic Insights
5. Brex — Data Analyst II
6. Mercury — Onboarding QC Specialist
7. ID.me — AI Creative Technologist *(may be intentionally cut by the new "Creative Technologist" exclusion — that's acceptable)*

Pass criteria: survivors ≤ 15 **and** ≥ 5 of the 6 non-creative-technologist roles still pass.

- [ ] **Step 3: If pass criteria not met, diagnose**

If too many survivors: examine which titles got through; tighten EXCLUDED_TITLES or POSITIVE_TITLE_KEYWORDS — but only after seeing actual examples.

If known-relevant roles got dropped: examine `result.reasons` for the dropped URL — almost certainly a missing positive keyword. Add the keyword.

- [ ] **Step 4: Commit verification log (optional)**

```bash
cp /tmp/scan-after.txt docs/superpowers/plans/2026-04-19-scan-after.txt
git add docs/superpowers/plans/2026-04-19-scan-after.txt
git commit -m "docs(jobscan): record post-filter scan output"
```

---

## Out of scope (intentionally deferred)

- **Compensation floor filter** (item 5 from the original list) — defer until a sample of the new filtered output shows comp data is reliably present in the descriptions.
- **JS scanner deletion** — leave `jobscan2/` in place. Decision on its fate is independent.
- **Workday/SmartRecruiters/Workable parsers** — would expand coverage but doesn't address the noise problem this plan targets.
- **Lane-specific positive matching** — current plan uses a single global positive list. If Lane 2/3 noise remains after Task 6, revisit with per-lane gates.
