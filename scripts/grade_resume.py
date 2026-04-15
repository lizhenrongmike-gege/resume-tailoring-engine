#!/usr/bin/env python3
"""Deterministic grading script for generated resumes.

Evaluates a generated resume JS script against its keyword YAML and scores
six automated dimensions. Outputs a grade YAML file.

Usage:
    python3 scripts/grade_resume.py <js_script> <keywords_yaml> [--output path]

If --output is omitted, derives slug from the JS filename and writes to
output/grades/{slug}_grade.yaml.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime

import yaml


# ---------------------------------------------------------------------------
# JS content parsing
# ---------------------------------------------------------------------------

def parse_js_content(js_path):
    """Extract the content object from a generated resume JS file via Node."""
    js_path_abs = os.path.abspath(js_path)

    node_code = r"""
const vm = require('vm');
const fs = require('fs');
const code = fs.readFileSync(process.argv[1], 'utf8');
const match = code.match(/const content = (\{[\s\S]*?^\});/m);
if (!match) {
    console.error('Could not find content object');
    process.exit(1);
}
try {
    const content = vm.runInNewContext('(' + match[1] + ')');
    console.log(JSON.stringify(content));
} catch (e) {
    console.error('Failed to parse content:', e.message);
    process.exit(1);
}
"""

    result = subprocess.run(
        ["node", "-e", node_code, js_path_abs],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to parse JS content: {result.stderr.strip()}")
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Keyword YAML parsing
# ---------------------------------------------------------------------------

def parse_keywords(yaml_path):
    """Load must_cover list from keyword YAML."""
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("must_cover", [])


# ---------------------------------------------------------------------------
# Helper: collect all bullets with role/project labels
# ---------------------------------------------------------------------------

def collect_bullets(content):
    """Return list of (label, bullet_text) tuples and item count."""
    items = []
    for role in content.get("workExperience", []):
        label = role.get("company", "Unknown")
        for bullet in role.get("bullets", []):
            items.append((label, bullet))
    for proj in content.get("selectedProjects", []):
        label = proj.get("name", "Unknown")
        for bullet in proj.get("bullets", []):
            items.append((label, bullet))
    return items


def collect_first_bullets(content):
    """Return list of (label, first_bullet_text) for each role/project."""
    firsts = []
    for role in content.get("workExperience", []):
        label = role.get("company", "Unknown")
        bullets = role.get("bullets", [])
        if bullets:
            firsts.append((label, bullets[0]))
    for proj in content.get("selectedProjects", []):
        label = proj.get("name", "Unknown")
        bullets = proj.get("bullets", [])
        if bullets:
            firsts.append((label, bullets[0]))
    return firsts


def count_items(content):
    """Count total roles + projects."""
    roles = len(content.get("workExperience", []))
    projects = len(content.get("selectedProjects", []))
    return roles, projects


# ---------------------------------------------------------------------------
# Metric detection
# ---------------------------------------------------------------------------

def has_metric(text):
    """Return True if the bullet contains a quantitative metric (not just a date)."""
    # Match percentages, dollar amounts, numbers with commas, plain numbers
    # but exclude date patterns like MM/YYYY or YYYY
    candidates = re.findall(r'\$[\d,]+[KkMmBb]?|\d[\d,]*\.?\d*[%+]|\d[\d,]*\+', text)
    if candidates:
        return True

    # Words indicating quantity
    if re.search(r'\b(?:million|billion|thousand)\b', text, re.IGNORECASE):
        return True

    # Find standalone numbers and filter out dates
    numbers = re.findall(r'\b(\d[\d,]*)\b', text)
    for num in numbers:
        raw = num.replace(",", "")
        # Skip if it looks like a year (4 digits, 19xx or 20xx)
        if re.match(r'^(19|20)\d{2}$', raw):
            continue
        # Skip if preceded by / (part of MM/YYYY) -- check in original text
        idx = text.find(num)
        if idx > 0 and text[idx - 1] == '/':
            continue
        # Skip if followed by / (part of MM/YYYY)
        end = idx + len(num)
        if end < len(text) and text[end] == '/':
            continue
        # This looks like a real metric number
        return True

    return False


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def score_bullet_structure(content):
    """Score bullet count and item count."""
    roles, projects = count_items(content)
    total_items = roles + projects

    work_bullets = sum(len(r.get("bullets", [])) for r in content.get("workExperience", []))
    proj_bullets = sum(len(p.get("bullets", [])) for p in content.get("selectedProjects", []))
    total_bullets = work_bullets + proj_bullets

    score = 100
    violations = []

    # Bullet count: 14-18 ideal
    if total_bullets < 14:
        penalty = (14 - total_bullets) * 15
        score -= penalty
        violations.append(f"Only {total_bullets} bullets (below minimum 14, -{penalty})")
    elif total_bullets > 18:
        penalty = (total_bullets - 18) * 15
        score -= penalty
        violations.append(f"{total_bullets} bullets (above maximum 18, -{penalty})")

    # Item count: 4-6 ideal
    if total_items < 4:
        penalty = (4 - total_items) * 20
        score -= penalty
        violations.append(f"Only {total_items} items (below minimum 4, -{penalty})")
    elif total_items > 6:
        penalty = (total_items - 6) * 20
        score -= penalty
        violations.append(f"{total_items} items (above maximum 6, -{penalty})")

    score = max(0, score)

    details = [
        f"Work experience: {roles} roles, {work_bullets} bullets",
        f"Projects: {projects} projects, {proj_bullets} bullets",
    ]

    return {
        "score": score,
        "total_bullets": total_bullets,
        "total_items": total_items,
        "details": details,
        "violations": violations,
    }


def score_bullet_length(content):
    """Score bullet word-length distribution."""
    all_bullets = collect_bullets(content)

    distribution = {"short": 0, "standard": 0, "long": 0, "violation": 0}
    violations = []

    for label, bullet in all_bullets:
        word_count = len(bullet.split())
        if word_count < 15 or word_count > 36:
            distribution["violation"] += 1
            if word_count < 15:
                violations.append(f"'{label}': {word_count} words (below 15)")
            else:
                violations.append(f"'{label}': {word_count} words (exceeds 36)")
        elif 15 <= word_count <= 20:
            distribution["short"] += 1
        elif 21 <= word_count <= 28:
            distribution["standard"] += 1
        elif 29 <= word_count <= 36:
            distribution["long"] += 1

    score = 100

    # Deduct 15 per violation
    score -= distribution["violation"] * 15

    # Deduct 10 if fewer than 4 SHORT
    if distribution["short"] < 4:
        score -= 10

    # Deduct 10 per excess LONG beyond 2
    if distribution["long"] > 2:
        score -= (distribution["long"] - 2) * 10

    score = max(0, score)

    return {
        "score": score,
        "distribution": distribution,
        "violations": violations,
    }


def score_metric_density(content):
    """Score how many bullets contain quantitative metrics."""
    all_bullets = collect_bullets(content)
    total = len(all_bullets)

    if total == 0:
        return {
            "score": 0,
            "quantified_bullets": 0,
            "total_bullets": 0,
            "percentage": 0.0,
            "first_bullet_results": [],
            "violations": [],
        }

    quantified = sum(1 for _, b in all_bullets if has_metric(b))
    percentage = (quantified / total) * 100

    # Percentage score (100 if >= 70%, linear down)
    if percentage >= 70:
        percentage_score = 100
    else:
        percentage_score = max(0, (percentage / 70) * 100)

    # First bullet score
    first_bullets = collect_first_bullets(content)
    first_bullet_results = []
    first_misses = 0
    for label, bullet in first_bullets:
        q = has_metric(bullet)
        first_bullet_results.append({"role": label, "quantified": q})
        if not q:
            first_misses += 1

    first_bullet_score = max(0, 100 - first_misses * 25)

    score = round(percentage_score * 0.6 + first_bullet_score * 0.4)
    score = max(0, min(100, score))

    violations = []
    for label, bullet in first_bullets:
        if not has_metric(bullet):
            violations.append(f"First bullet of '{label}' lacks a metric")

    return {
        "score": score,
        "quantified_bullets": quantified,
        "total_bullets": total,
        "percentage": round(percentage, 1),
        "first_bullet_results": first_bullet_results,
        "violations": violations,
    }


def score_keyword_coverage(keywords):
    """Score keyword placement from keyword YAML data."""
    total = len(keywords)
    if total == 0:
        return {
            "score": 100,
            "placed": 0,
            "missing": 0,
            "total": 0,
            "hard_req_placed": 0,
            "hard_req_total": 0,
            "missing_keywords": [],
        }

    placed = sum(1 for k in keywords if k.get("status", "").upper() == "PLACED")
    missing = total - placed

    hard_req_total = sum(1 for k in keywords if k.get("type", "") == "hard_req")
    hard_req_placed = sum(
        1 for k in keywords
        if k.get("type", "") == "hard_req" and k.get("status", "").upper() == "PLACED"
    )

    placement_rate = placed / total if total > 0 else 0
    hard_req_rate = hard_req_placed / hard_req_total if hard_req_total > 0 else 1.0

    score = round((placement_rate * 0.5 + hard_req_rate * 0.5) * 100)
    score = max(0, min(100, score))

    missing_keywords = [
        {"keyword": k["keyword"], "type": k.get("type", "unknown")}
        for k in keywords if k.get("status", "").upper() != "PLACED"
    ]

    return {
        "score": score,
        "placed": placed,
        "missing": missing,
        "total": total,
        "hard_req_placed": hard_req_placed,
        "hard_req_total": hard_req_total,
        "missing_keywords": missing_keywords,
    }


def score_verb_quality(content):
    """Score action verb quality: no banned verbs, good variety."""
    BANNED_STARTS = [
        "responsible", "assisted", "helped", "participated",
        "handled", "utilized", "supported", "contributed",
    ]

    all_bullets = collect_bullets(content)
    first_words = []
    for _, bullet in all_bullets:
        words = bullet.strip().split()
        if words:
            first_words.append(words[0])

    word_counts = Counter(first_words)

    score = 100
    banned_found = []
    repeated_verbs = []

    for word in first_words:
        if word.lower() in BANNED_STARTS and word not in banned_found:
            banned_found.append(word)
            score -= 20

    for word, count in word_counts.items():
        if count >= 3:
            repeated_verbs.append(f"{word} (used {count} times)")
            score -= (count - 2) * 10

    score = max(0, score)

    return {
        "score": score,
        "first_words": dict(word_counts),
        "banned_found": banned_found,
        "repeated_verbs": repeated_verbs,
    }


def score_summary_length(content):
    """Score summary brevity."""
    summary = content.get("summary", "")
    word_count = len(summary.split())

    if word_count <= 45:
        score = 100
    else:
        score = max(0, 100 - (word_count - 45) * 5)

    return {
        "score": score,
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# Slug derivation
# ---------------------------------------------------------------------------

def derive_slug(js_filename):
    """Derive slug from JS filename, e.g. generate_accuris_resume.js -> accuris."""
    name = os.path.basename(js_filename)
    # Remove generate_ prefix and _resume.js suffix
    name = re.sub(r'^generate_', '', name)
    name = re.sub(r'_resume\.js$', '', name)
    return name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Grade a generated resume against quality criteria."
    )
    parser.add_argument("js_script", help="Path to the generated JS resume script")
    parser.add_argument("keywords_yaml", help="Path to the keyword YAML file")
    parser.add_argument(
        "--output", "-o",
        help="Output path for grade YAML (default: output/grades/{slug}_grade.yaml)",
    )
    args = parser.parse_args()

    # Validate inputs
    if not os.path.isfile(args.js_script):
        print(f"Error: JS script not found: {args.js_script}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.keywords_yaml):
        print(f"Error: Keywords YAML not found: {args.keywords_yaml}", file=sys.stderr)
        sys.exit(1)

    # Parse inputs
    try:
        content = parse_js_content(args.js_script)
    except Exception as e:
        print(f"Error parsing JS content: {e}", file=sys.stderr)
        sys.exit(1)

    keywords = parse_keywords(args.keywords_yaml)

    # Derive slug and output path
    slug = derive_slug(args.js_script)
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join("output", "grades", f"{slug}_grade.yaml")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Score all dimensions
    bullet_struct = score_bullet_structure(content)
    bullet_len = score_bullet_length(content)
    metric_dens = score_metric_density(content)
    keyword_cov = score_keyword_coverage(keywords)
    verb_qual = score_verb_quality(content)
    summary_len = score_summary_length(content)

    # Build output
    grade = {
        "slug": slug,
        "graded_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "script_path": args.js_script,
        "keywords_path": args.keywords_yaml,
        "overall_score": None,
        "dimensions": {
            "bullet_structure": bullet_struct,
            "bullet_length": bullet_len,
            "metric_density": metric_dens,
            "keyword_coverage": keyword_cov,
            "verb_quality": verb_qual,
            "summary_length": summary_len,
            "xyz_formula": None,
            "keyword_contextual_placement": None,
            "summary_quality": None,
            "reframing_integrity": None,
        },
    }

    # Write YAML
    with open(output_path, "w") as f:
        yaml.dump(grade, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Print summary
    print(
        f"Grade: {slug}"
        f" | Bullets: {bullet_struct['score']}"
        f" | Length: {bullet_len['score']}"
        f" | Metrics: {metric_dens['score']}"
        f" | Keywords: {keyword_cov['score']}"
        f" | Verbs: {verb_qual['score']}"
        f" | Summary: {summary_len['score']}"
    )
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
