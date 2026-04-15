#!/usr/bin/env python3
"""
build_ledger.py — Scaffold career_ledger.yaml from a Resume Bank .docx

Extracts text via pandoc, parses sections (Work Experience, Projects,
Education, Skills), and writes a YAML skeleton with TODO placeholders
for fields that require human judgment.

Usage:
    python3 scripts/build_ledger.py [--force] [input_path] [output_path]

Defaults:
    input:  inputs/resume_bank.docx
    output: career_ledger.yaml

Options:
    --force   Overwrite existing output without prompting

After running, the agent reviews the output and fills in every TODO:
    - plausibility_ceiling  (role/project-level guardrail)
    - reframe_ceiling       (per-achievement guardrail)
    - keywords_natural      (organic keywords each achievement supports)
    - method                (tools, techniques, processes used)
    - outcome               (business result or downstream impact)
    - Refine 'action' from raw bullet text to concise description
    - Verify/expand tools_confirmed lists
"""

import sys
import os
import re
import subprocess

# ── Constants ────────────────────────────────────────────────────────

MONTH_NAMES = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_RANGE_RE = re.compile(
    rf"({MONTH_NAMES}\.?\s+\d{{4}})\s*[-–—]+\s*({MONTH_NAMES}\.?\s+\d{{4}}|Present)",
    re.IGNORECASE,
)

SECTION_RE = re.compile(
    r"^(EDUCATION|WORK\s+EXPERIENCE|RESEARCH\s+PROJECTS?"
    r"|TECHNICAL\s+SKILLS|ADDITIONAL\s+CONTENT[^\n]*|PROJECTS?)$",
    re.MULTILINE | re.IGNORECASE,
)

MONTH_TO_NUM = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

# Multi-word entries must come before their single-word components.
# "R" is intentionally excluded — it false-positives on words like
# "Reduced", "Risk", "Research", etc.
KNOWN_TOOLS = [
    "Vertex AI", "Google ADK", "Scikit-learn", "pivot tables",
    "logistic regression", "BG/NBD", "Gamma-Gamma", "Node.js", "docx-js",
    "Python", "SQL", "JavaScript", "Bash", "Stata",
    "Tableau", "Excel", "Salesforce", "Shopify", "Squarespace",
    "Gemini", "Pandas", "NumPy", "XLOOKUP",
    "TikTok", "Amazon", "Instagram",
    "Pandoc", "YAML", "Git", "GitHub",
    "WLS", "DCF", "ETL",
]

ROLE_KEYWORDS = [
    "engineer", "analyst", "intern", "lead", "founder", "manager",
    "director", "assistant", "associate", "specialist", "coordinator",
    "co-founder",
]

# Domain vocabulary for auto-populating keywords_natural.
# Multi-word phrases first (matched before single words to avoid partial hits).
# This list covers common JD vocabulary across tech, analytics, business, and
# operations roles — extend it when targeting new domains.
DOMAIN_KEYWORDS = [
    # Data & Analytics
    "root cause analysis", "data reconciliation", "data validation",
    "data pipeline", "data analysis", "data engineering",
    "feature engineering", "data cleaning", "data extraction",
    "predictive model", "statistical analysis", "regression analysis",
    "time series", "A/B testing",
    # AI & ML
    "AI agent", "machine learning", "prompt engineering",
    "large language model", "natural language processing",
    "computer vision", "model training", "model deployment",
    # Risk & Compliance
    "risk management", "risk assessment", "risk analysis", "risk model",
    "credit risk", "case management", "case triage", "link analysis",
    "pattern detection", "fraud detection", "fraud prevention",
    "coordinated abuse", "risk segmentation",
    # Business & Operations
    "cross-functional", "go-to-market", "product roadmap",
    "unit economics", "market analysis", "competitive analysis",
    "due diligence", "investment thesis", "deal sourcing",
    "customer lifetime value", "cost modeling", "financial analysis",
    # Process & Workflow
    "process improvement", "workflow automation", "case routing",
    "quality assurance", "data-driven", "data preparation",
    # Single-word domain terms
    "automation", "analytics", "compliance", "KYC", "sanctions",
    "onboarding", "enforcement", "triage", "reconciliation",
    "dashboard", "reporting", "visualization", "scraping",
    "pipeline", "deployment", "API", "multimodal", "chatbot",
    "workflow", "operations", "retention", "revenue", "pricing",
    "segmentation", "classification", "optimization", "forecasting",
    "adjudication", "deduplication", "normalization", "ingestion",
    "NLP", "LLM", "NPV", "LTV", "CLV", "ROI", "SKU", "TAM",
]

# Words that commonly appear before role keywords but belong to the role title,
# not the company name. Used when parsing single-line headers.
ROLE_PREFIXES = {
    "data", "credit", "risk", "research", "senior", "junior",
    "venture", "product", "ai", "software", "business", "marketing",
}

# Words that should NEVER be treated as part of a city name.
# Prevents "Bank Ningbo" or "Packaging Ningbo" from being parsed as locations.
NOT_CITY_WORDS = {
    "bank", "group", "college", "company", "corporation", "inc", "ltd",
    "packaging", "tech", "center", "university", "institute", "labs",
    "systems", "solutions", "services", "global", "international",
}


# ── Text extraction ─────────────────────────────────────────────────

def extract_text(docx_path):
    """Run pandoc to convert .docx to unwrapped plain text."""
    if not os.path.isfile(docx_path):
        sys.exit(f"Error: file not found: {docx_path}")
    result = subprocess.run(
        ["pandoc", docx_path, "-t", "plain", "--wrap=none"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"pandoc error: {result.stderr.strip()}")
    return result.stdout


# ── Section splitting ────────────────────────────────────────────────

def split_sections(text):
    """Return {NORMALIZED_HEADER: body_text} for each major section."""
    matches = list(SECTION_RE.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        key = re.sub(r"\s+", " ", m.group(0).strip().upper())
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[key] = text[m.end() : end].strip()
    return sections


# ── Helpers ──────────────────────────────────────────────────────────

def normalize_date(month_year_str):
    """Convert 'Jan 2026' to '01/2026'. Returns as-is if unparseable."""
    parts = month_year_str.strip().split()
    if len(parts) == 2:
        m = MONTH_TO_NUM.get(parts[0].lower().rstrip("."))
        if m:
            return f"{m}/{parts[1]}"
    return month_year_str.strip()


def find_date_range(text):
    """Return (normalized 'MM/YYYY - MM/YYYY', text-without-dates) or (None, text)."""
    m = DATE_RANGE_RE.search(text)
    if not m:
        return None, text
    start = normalize_date(m.group(1))
    end = m.group(2).strip()
    if end.lower() != "present":
        end = normalize_date(end)
    dates = f"{start} - {end}"
    rest = (text[: m.start()] + " " + text[m.end() :]).strip()
    return dates, rest


def extract_location(text):
    """
    Extract a location from the end of a text string.
    Returns (location, text_with_location_removed).
    Handles 'Remote', 'City, ST', 'City Name, ST', 'City, China',
    and reversed 'ST, City' (pandoc tab-stop artifact).

    All patterns are end-anchored to avoid grabbing company-name words
    (e.g., "Bank" in "China Construction Bank Ningbo, China").
    """
    # Check for "Remote" at end
    m = re.search(r"\s+(Remote)\s*$", text, re.IGNORECASE)
    if m:
        return "Remote", text[: m.start()].strip()

    # Two-word city at end: "Chestnut Hill, MA"
    # Reject if first word is a known non-city word (e.g., "Bank", "Packaging")
    m = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+),\s*([A-Z]{2}|China)\s*$", text)
    if m and m.group(1).split()[0].lower() not in NOT_CITY_WORDS:
        location = f"{m.group(1)}, {m.group(2)}"
        return location, text[: m.start()].strip()

    # Single-word city at end: "Sunnyvale, CA" or "Ningbo, China"
    m = re.search(r"([A-Z][a-z]+),\s*([A-Z]{2}|China)\s*$", text)
    if m:
        location = f"{m.group(1)}, {m.group(2)}"
        return location, text[: m.start()].strip()

    # Reversed "ST, City" at end (pandoc sometimes swaps tab-stop order)
    # e.g., "Ant Group CA, Sunnyvale" → extract "Sunnyvale, CA"
    m = re.search(r"([A-Z]{2}),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$", text)
    if m:
        location = f"{m.group(2)}, {m.group(1)}"
        return location, text[: m.start()].strip()

    return "TODO", text


def extract_metric(bullet):
    """Return (metric_string, metric_type) from bullet text."""
    # Dollar amounts
    dollars = re.findall(r"\$[\d,]+\+?", bullet)
    if dollars:
        return ", ".join(dollars), "dollar"
    # Percentages
    pcts = re.findall(r"\d+(?:\.\d+)?%", bullet)
    if pcts:
        return ", ".join(pcts), "percentage"
    # Scale numbers (2+ digits, optionally with K/M/+ suffix)
    nums = re.findall(r"\d[\d,]*\+?[KMB]?", bullet)
    meaningful = [n for n in nums if len(n.replace(",", "").rstrip("+KMB")) >= 2]
    if meaningful:
        return ", ".join(meaningful[:3]), "scale"
    return None, "none"


def detect_tools(text):
    """Return sorted, deduplicated list of known tools mentioned in text."""
    found = {}  # lowercase → canonical form
    for tool in KNOWN_TOOLS:
        # Use word boundaries to avoid false positives (e.g. "Git" in "logit")
        pattern = r"\b" + re.escape(tool) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            low = tool.lower()
            if low not in found:
                found[low] = tool
    return sorted(found.values())


def extract_keywords(text, bullet_tools):
    """Extract keywords_natural for an achievement from its bullet text.

    Combines:
    - Per-bullet tools (achievement-level specificity, not role-level)
    - Domain keywords matched from DOMAIN_KEYWORDS list

    Returns a sorted, deduplicated list, or ["TODO"] if nothing found.
    """
    found = set()
    # Include per-bullet tools (gives achievement-level tool specificity)
    for tool in bullet_tools:
        found.add(tool)
    # Match domain keywords from bullet text
    for kw in DOMAIN_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            found.add(kw)
    return sorted(found) if found else ["TODO"]


# Track used IDs globally to prevent collisions across merged entries
_used_ids = set()


def make_id(name, index):
    """Generate a unique achievement ID like 'nuonc_1'."""
    short = re.sub(r"[^a-zA-Z]", "", name.split()[0] if name else "x").lower()
    candidate = f"{short}_{index}"
    if candidate in _used_ids:
        suffix = "b"
        while f"{candidate}{suffix}" in _used_ids:
            suffix = chr(ord(suffix) + 1)
        candidate = f"{candidate}{suffix}"
    _used_ids.add(candidate)
    return candidate


# ── Entry parsing ────────────────────────────────────────────────────

def parse_entries(section_text):
    """
    Split a section into entries: list of (header_lines, [bullet_strings]).

    Bullets start with '- ' or '• '.  Everything else is header text.
    Blank lines between bullets are IGNORED (pandoc inserts them).
    A new entry starts when a non-bullet, non-empty line appears after
    one or more bullets have already been collected.
    """
    lines = section_text.split("\n")
    entries = []
    headers = []
    bullets = []

    for raw_line in lines:
        line = raw_line.strip()

        # Skip blank lines — they do NOT signal entry boundaries
        if not line:
            continue

        if line.startswith("- ") or line.startswith("• "):
            bullets.append(line.lstrip("-•").strip())
        else:
            if bullets:
                # Non-bullet line after bullets = start of a new entry
                entries.append((list(headers), list(bullets)))
                headers = [line]
                bullets = []
            else:
                headers.append(line)

    # Flush the last entry
    if bullets:
        entries.append((list(headers), list(bullets)))
    return entries


def parse_work_header(header_lines):
    """Extract role, company, location, dates from 1-3 header lines."""
    combined = " ".join(header_lines)
    dates, _ = find_date_range(combined)

    company = "TODO"
    role = "TODO"
    location = "TODO"

    if len(header_lines) >= 2:
        line1 = header_lines[0].strip()
        line2 = header_lines[1].strip()
        _, line2_clean = find_date_range(line2)

        # Default assumption: line1 = company + location, line2 = role + dates.
        # Override if line1 contains role keywords and line2 does not.
        line1_has_role = any(kw in line1.lower() for kw in ROLE_KEYWORDS)
        line2_has_role = any(kw in line2_clean.lower() for kw in ROLE_KEYWORDS)

        if line1_has_role and not line2_has_role:
            # Swapped: line1 is role, line2 is company
            role = line1.strip()
            location, company_text = extract_location(line2_clean)
            company = company_text.strip() if company_text else "TODO"
        else:
            # Standard: line1 is company, line2 is role
            location, company_text = extract_location(line1)
            company = company_text.strip() if company_text else "TODO"
            role = line2_clean.strip()

    elif len(header_lines) == 1:
        # Everything on one line — find role keyword first to split
        # company+location from role title
        _, no_dates = find_date_range(header_lines[0])

        # Find the earliest role keyword (word-boundary check to avoid
        # matching inside other words like "engineering")
        best_idx = -1
        for kw in ROLE_KEYWORDS:
            idx = no_dates.lower().find(kw)
            if idx > 0 and (best_idx == -1 or idx < best_idx):
                if not no_dates[idx - 1].isalpha():
                    best_idx = idx

        if best_idx > 0:
            company_loc = no_dates[:best_idx].strip()
            role = no_dates[best_idx:].strip()
            # Strip role-prefix words from end of company portion
            # e.g., "Gedia Packaging Ningbo, China Data" → move "Data" to role
            words = company_loc.split()
            while words and words[-1].lower().rstrip(",") in ROLE_PREFIXES:
                role = words.pop().rstrip(",") + " " + role
            company_loc = " ".join(words).rstrip(",")
            location, company_text = extract_location(company_loc)
            company = company_text.strip() if company_text else "TODO"
        else:
            location, remaining = extract_location(no_dates)
            role = remaining.strip()

    return {
        "company": company or "TODO",
        "role": role or "TODO",
        "location": location or "TODO",
        "dates": dates or "TODO",
    }


def parse_project_header(header_lines):
    """Extract project name and dates from header lines."""
    combined = " ".join(header_lines)
    dates, remaining = find_date_range(combined)
    # Strip trailing pipe-separated tool lists
    name = remaining.split("|")[0].strip().rstrip(",")
    return {"name": name or "TODO", "dates": dates or "TODO"}


def parse_education(section_text):
    """Parse education section into structured data."""
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    edu = {
        "institution": "TODO",
        "location": "TODO",
        "degree": "TODO",
        "gpa": "TODO",
        "graduation": "TODO",
        "relevant_coursework": [],
    }

    for line in lines:
        # Look for GPA
        gpa_match = re.search(r"GPA:\s*([\d.]+\s*/\s*[\d.]+)", line)
        if gpa_match:
            edu["gpa"] = gpa_match.group(1).replace(" ", "")

        # Look for degree — use word boundaries to avoid matching
        # "Machine" (contains "Ma" which looks like M.A. without boundaries)
        if re.search(r"\b(?:Bachelor|Master|Ph\.?D)\b", line, re.IGNORECASE):
            dates, degree_text = find_date_range(line)
            if dates:
                edu["graduation"] = dates.split(" - ")[-1].strip()
            # Clean up degree text
            degree_text = re.sub(r"GPA:\s*[\d./\s]+", "", degree_text).strip()
            if degree_text:
                edu["degree"] = degree_text

        # Look for coursework
        if re.search(r"relevant\s+course|coursework", line, re.IGNORECASE):
            courses_text = re.sub(r"^.*?:\s*", "", line)
            edu["relevant_coursework"] = [
                c.strip().rstrip(".") for c in courses_text.split(",") if c.strip()
            ]

        # Look for institution (first line without degree/coursework keywords)
        if not any(kw in line.lower() for kw in ["bachelor", "master", "gpa", "course", "relevant"]):
            loc, inst_text = extract_location(line)
            if loc != "TODO" and edu["institution"] == "TODO":
                edu["location"] = loc
                edu["institution"] = inst_text.strip().rstrip(",")

    return edu


def parse_skills(section_text):
    """Parse technical skills section into categorized lists."""
    items = [s.strip().rstrip(".") for s in re.split(r"[,;]", section_text) if s.strip()]

    languages = []
    tools = []
    frameworks = []
    methods = []

    lang_kw = {"python", "sql", "javascript", "bash", "stata", "node.js"}
    framework_kw = {"vertex ai", "google adk", "gemini", "scikit-learn", "pandas", "numpy"}
    method_kw = {"etl", "regression", "scraping", "reconciliation", "modeling"}

    for item in items:
        low = item.lower()
        # Handle parenthetical sub-items like "Python (Pandas, NumPy, Scikit-learn)"
        paren = re.match(r"(.+?)\s*\(([^)]+)\)", item)
        if paren:
            main = paren.group(1).strip()
            subs = [s.strip() for s in paren.group(2).split(",")]
            if main.lower() in lang_kw:
                languages.append(main)
            for sub in subs:
                if sub.lower() in framework_kw:
                    frameworks.append(sub)
                else:
                    tools.append(sub)
            continue

        if low in lang_kw:
            languages.append(item)
        elif low in framework_kw:
            frameworks.append(item)
        elif any(m in low for m in method_kw):
            methods.append(item)
        else:
            tools.append(item)

    return {
        "languages": languages,
        "tools": tools,
        "frameworks": frameworks,
        "methods": methods,
    }


# ── Duplicate merging ────────────────────────────────────────────────

def normalize_company(name):
    """Remove parenthetical notes, collapse whitespace, lowercase."""
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", name)).strip().lower()


def merge_duplicate_entries(entries):
    """Merge work entries with the same normalized company name.

    Combines bullets (deduped) and keeps the header that parsed better
    (prefers resolved location over TODO). Returns merged list in
    original insertion order.
    """
    groups = {}  # normalized_name → [headers, bullets]

    for headers, bullets in entries:
        info = parse_work_header(headers)
        key = normalize_company(info["company"])
        if key in ("todo", ""):
            key = f"_unknown_{len(groups)}"

        if key in groups:
            grp_h, grp_b = groups[key]
            # Keep the header that has a resolved location
            old_info = parse_work_header(grp_h)
            if old_info["location"] == "TODO" and info["location"] != "TODO":
                groups[key][0] = list(headers)
            # Append non-duplicate bullets
            seen = set(grp_b)
            for b in bullets:
                if b not in seen:
                    grp_b.append(b)
            print(f"  Merged duplicate entry for: {info['company']}")
        else:
            groups[key] = [list(headers), list(bullets)]

    return [tuple(v) for v in groups.values()]


# ── YAML formatting ─────────────────────────────────────────────────

def yq(s):
    """Quote a string for YAML. Returns 'none' unquoted for None values."""
    if s is None:
        return "none"
    escaped = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(items):
    """Format a list inline: [item1, item2]."""
    if not items:
        return "[TODO]"
    return "[" + ", ".join(str(i) for i in items) + "]"


# ── Output generation ────────────────────────────────────────────────

def write_work_section(entries, f):
    """Write work_experience section to file."""
    f.write("work_experience:\n")
    for headers, bullets in entries:
        if not bullets:
            continue
        info = parse_work_header(headers)
        all_text = " ".join(bullets)
        tools = detect_tools(all_text)

        f.write(f'  - role: {yq(info["role"])}\n')
        f.write(f'    company: {yq(info["company"])}\n')
        f.write(f'    location: {yq(info["location"])}\n')
        f.write(f'    dates: {yq(info["dates"])}\n')
        f.write(f'    tools_confirmed: {yaml_list(tools)}  # TODO: verify and expand\n')
        f.write(f'    plausibility_ceiling: "TODO — set role-level guardrail: what framing is honest vs. fabrication for this role"\n')
        f.write(f'    achievements:\n')

        for i, bullet in enumerate(bullets, 1):
            metric_val, metric_type = extract_metric(bullet)
            aid = make_id(info["company"], i)
            bullet_tools = detect_tools(bullet)

            f.write(f"      - id: {aid}\n")
            f.write(f"        action: {yq(bullet)}\n")
            if metric_val:
                f.write(f"        metric: {yq(metric_val)}\n")
            else:
                f.write(f"        metric: none\n")
            f.write(f"        metric_type: {metric_type}\n")
            if bullet_tools:
                f.write(f"        method: {yq(', '.join(bullet_tools))}  # TODO: refine — auto-detected tools\n")
            else:
                f.write(f'        method: "TODO — extract tools, techniques, processes from action"\n')
            f.write(f'        outcome: "TODO — business result or downstream impact"\n')
            f.write(f'        reframe_ceiling: "TODO — what can be reframed vs. what would be fabrication"\n')
            bullet_keywords = extract_keywords(bullet, bullet_tools)
            f.write(f"        keywords_natural: {yaml_list(bullet_keywords)}\n")

        f.write("\n")


def write_projects_section(entries, f):
    """Write independent_projects section to file."""
    f.write("independent_projects:\n")
    for headers, bullets in entries:
        if not bullets:
            continue
        info = parse_project_header(headers)
        all_text = " ".join(headers) + " " + " ".join(bullets)
        tools = detect_tools(all_text)

        f.write(f'  - project_name: {yq(info["name"])}\n')
        f.write(f'    tools_confirmed: {yaml_list(tools)}  # TODO: verify and expand\n')
        f.write(f'    link: "TODO — GitHub repo, live demo, or portfolio URL if available"\n')
        f.write(f'    plausibility_ceiling: "TODO — set project-level guardrail"\n')
        f.write(f'    achievements:\n')

        for i, bullet in enumerate(bullets, 1):
            metric_val, metric_type = extract_metric(bullet)
            aid = make_id(info["name"], i)
            bullet_tools = detect_tools(bullet)

            f.write(f"      - id: {aid}\n")
            f.write(f"        action: {yq(bullet)}\n")
            if metric_val:
                f.write(f"        metric: {yq(metric_val)}\n")
            else:
                f.write(f"        metric: none\n")
            f.write(f"        metric_type: {metric_type}\n")
            if bullet_tools:
                f.write(f"        method: {yq(', '.join(bullet_tools))}  # TODO: refine — auto-detected tools\n")
            else:
                f.write(f'        method: "TODO — extract tools, techniques, processes from action"\n')
            f.write(f'        outcome: "TODO — business result or downstream impact"\n')
            f.write(f'        reframe_ceiling: "TODO — what can be reframed vs. what would be fabrication"\n')
            bullet_keywords = extract_keywords(bullet, bullet_tools)
            f.write(f"        keywords_natural: {yaml_list(bullet_keywords)}\n")

        f.write("\n")


def write_education_section(edu, f):
    """Write education section to file."""
    f.write("education:\n")
    f.write(f'  - institution: {yq(edu["institution"])}\n')
    f.write(f'    location: {yq(edu["location"])}\n')
    f.write(f'    degree: {yq(edu["degree"])}\n')
    f.write(f'    gpa: {yq(edu["gpa"])}\n')
    f.write(f'    graduation: {yq(edu["graduation"])}\n')
    f.write(f'    relevant_coursework: {yaml_list(edu["relevant_coursework"])}\n')
    f.write(f"    keywords_natural: [TODO]\n")


def write_skills_section(skills, extra_tools, f):
    """Write skills_confirmed section. Merges parsed skills with tools detected in bullets."""
    lang_kw = {"python", "sql", "javascript", "bash", "stata", "node.js"}
    framework_kw = {"vertex ai", "google adk", "gemini", "scikit-learn", "pandas", "numpy"}

    all_langs = set(s.lower() for s in skills["languages"])
    all_tools = set(s.lower() for s in skills["tools"])
    all_fw = set(s.lower() for s in skills["frameworks"])

    for tool in extra_tools:
        low = tool.lower()
        if low in lang_kw and low not in all_langs:
            skills["languages"].append(tool)
            all_langs.add(low)
        elif low in framework_kw and low not in all_fw:
            skills["frameworks"].append(tool)
            all_fw.add(low)
        elif low not in all_tools and low not in all_langs and low not in all_fw:
            skills["tools"].append(tool)
            all_tools.add(low)

    f.write("\nskills_confirmed:  # TODO: verify completeness\n")
    f.write(f'  languages: {yaml_list(skills["languages"])}\n')
    f.write(f'  tools: {yaml_list(skills["tools"])}\n')
    f.write(f'  frameworks: {yaml_list(skills["frameworks"])}\n')
    f.write(f'  methods: {yaml_list(skills["methods"])}\n')


# ── Main ─────────────────────────────────────────────────────────────

def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    input_path = args[0] if len(args) > 0 else "inputs/resume_bank.docx"
    output_path = args[1] if len(args) > 1 else "career_ledger.yaml"

    # Guard against overwriting an existing ledger
    if os.path.isfile(output_path) and not force:
        if not sys.stdin.isatty():
            print(f"Error: {output_path} exists. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)
        resp = input(f"Overwrite {output_path}? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted. Existing ledger preserved.", file=sys.stderr)
            sys.exit(0)

    print(f"Extracting text from {input_path}...")
    text = extract_text(input_path)

    print("Splitting into sections...")
    sections = split_sections(text)

    # Collect all tools detected across all bullets for the skills section
    all_detected_tools = set()

    with open(output_path, "w") as f:
        # Work Experience
        work_keys = [k for k in sections if "WORK" in k and "EXPERIENCE" in k]
        if work_keys:
            entries = parse_entries(sections[work_keys[0]])
            # Also include ADDITIONAL CONTENT entries as extra work entries
            extra_keys = [k for k in sections if "ADDITIONAL" in k]
            for ek in extra_keys:
                extra = parse_entries(sections[ek])
                entries.extend(extra)
            # Merge duplicate entries (same company across sections)
            entries = merge_duplicate_entries(entries)
            for _, bullets in entries:
                all_detected_tools.update(detect_tools(" ".join(bullets)))
            write_work_section(entries, f)

        # Projects (RESEARCH PROJECTS)
        proj_keys = [k for k in sections if "PROJECT" in k and "RESEARCH" in k]
        if not proj_keys:
            proj_keys = [k for k in sections if "PROJECT" in k]
        if proj_keys:
            entries = parse_entries(sections[proj_keys[0]])
            for _, bullets in entries:
                all_detected_tools.update(detect_tools(" ".join(bullets)))
            write_projects_section(entries, f)

        # Education
        edu_keys = [k for k in sections if "EDUCATION" in k]
        if edu_keys:
            edu = parse_education(sections[edu_keys[0]])
            write_education_section(edu, f)

        # Skills
        f.write("\n")
        skill_keys = [k for k in sections if "SKILL" in k]
        if skill_keys:
            skills = parse_skills(sections[skill_keys[0]])
        else:
            skills = {"languages": [], "tools": [], "frameworks": [], "methods": []}
        write_skills_section(skills, all_detected_tools, f)

    # Summary
    print(f"\nScaffolded ledger written to: {output_path}")
    print(f"Detected tools across all entries: {sorted(all_detected_tools)}")
    print()
    print("Next steps — review the YAML and fill in every TODO:")
    print("  1. plausibility_ceiling — role/project-level guardrail")
    print("  2. reframe_ceiling     — per-achievement guardrail")
    print("  3. keywords_natural    — organic keywords per achievement")
    print("  4. method / outcome    — refine auto-detected values")
    print("  5. action              — distill raw bullet to concise description")
    print("  6. tools_confirmed     — verify and expand auto-detected lists")
    print("  7. Verify company, role, location, and dates — fix any parsing errors")


if __name__ == "__main__":
    main()
