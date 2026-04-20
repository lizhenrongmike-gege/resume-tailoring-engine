#!/usr/bin/env python3
"""JobScan — Daily job scanner CLI.

Usage:
    python3 jobscan/scan.py                  # run all enabled tiers
    python3 jobscan/scan.py --tier1          # run only Tier 1 (ATS APIs)
    python3 jobscan/scan.py --tier2          # run only Tier 2 (web search)
    python3 jobscan/scan.py --tier3          # run only Tier 3 (JobSpy)
    python3 jobscan/scan.py --tier1 --tier3  # run Tier 1 + Tier 3
    python3 jobscan/scan.py --lane 1         # scan specific lane
    python3 jobscan/scan.py --days 3         # only last 3 days
    python3 jobscan/scan.py history          # show scan history
    python3 jobscan/scan.py export           # export to batch_jds_auto.xlsx
    python3 jobscan/scan.py mark <company> <title> <status>
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env file from project root
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from jobscan.config import LANES, PRIORITY_COMPANIES
from jobscan.connectors.greenhouse import GreenhouseConnector
from jobscan.connectors.lever import LeverConnector
from jobscan.connectors.ashby import AshbyConnector
from jobscan.connectors.base import RawPosting
from jobscan.filters import apply_hard_filters
from jobscan.ranker import JobRanker
from jobscan.db import JobScanDB
from jobscan.report import generate_report
from jobscan.exporter import export_to_xlsx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Connector instances
_CONNECTORS = {
    "greenhouse": GreenhouseConnector(),
    "lever": LeverConnector(),
    "ashby": AshbyConnector(),
}


def _env_bool(key: str) -> bool:
    return os.environ.get(key, "true").lower() in ("true", "1", "yes")


def _get_db() -> JobScanDB:
    db_path = os.environ.get("JOBSCAN_DB_PATH", "jobscan/jobscan.db")
    return JobScanDB(db_path)


# ── Search Tiers (each is independent) ──────────────────────────────


def run_tier1(days_back: int) -> list[RawPosting]:
    """Tier 1: Direct ATS APIs for priority companies."""
    logger.info("═══ Tier 1: Scanning %d priority companies ═══", len(PRIORITY_COMPANIES))
    postings: list[RawPosting] = []

    for company in PRIORITY_COMPANIES:
        if company.get("enabled", True) is False:
            continue
        ats = company["ats"]
        if ats not in _CONNECTORS:
            logger.warning("  Unknown ATS '%s' for %s — skipping", ats, company["name"])
            continue

        connector = _CONNECTORS[ats]
        try:
            found = connector.fetch_company(
                slug=company["slug"],
                company_name=company["name"],
                days_back=days_back,
            )
            if found:
                logger.info("  %s: %d postings", company["name"], len(found))
            postings.extend(found)
        except NotImplementedError:
            pass
        time.sleep(0.5)

    logger.info("  Tier 1 total: %d postings", len(postings))
    return postings


def run_tier2(days_back: int, lane_filter: int | None) -> list[RawPosting]:
    """Tier 2: Anthropic web search discovery."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("No ANTHROPIC_API_KEY — skipping Tier 2")
        return []

    logger.info("═══ Tier 2: Web search discovery ═══")
    from jobscan.connectors.websearch import WebSearchConnector
    ws_conn = WebSearchConnector(api_key=api_key)

    lanes_to_search = LANES if not lane_filter else [
        l for l in LANES if l["id"] == lane_filter
    ]

    postings: list[RawPosting] = []
    for lane in lanes_to_search:
        try:
            found = ws_conn.search(
                keywords=lane["search_keywords"][:3],
                location="Bay Area",
                days_back=days_back,
            )
            if found:
                logger.info("  Lane %d: %d results", lane["id"], len(found))
            postings.extend(found)
        except Exception as e:
            logger.warning("  Lane %d web search failed: %s", lane["id"], e)

    logger.info("  Tier 2 total: %d postings", len(postings))
    return postings


def run_tier3(days_back: int, lane_filter: int | None) -> list[RawPosting]:
    """Tier 3: JobSpy aggregator (Indeed, LinkedIn, Glassdoor, Google)."""
    logger.info("═══ Tier 3: JobSpy aggregator ═══")
    from jobscan.connectors.jobspy_connector import JobSpyConnector

    sites_str = os.environ.get("JOBSPY_SITES", "indeed,linkedin,glassdoor,google")
    sites = [s.strip() for s in sites_str.split(",")]
    results_wanted = int(os.environ.get("JOBSPY_RESULTS_PER_KEYWORD", "15"))

    connector = JobSpyConnector(sites=sites, results_wanted=results_wanted)

    lanes_to_search = LANES if not lane_filter else [
        l for l in LANES if l["id"] == lane_filter
    ]

    postings: list[RawPosting] = []
    for lane in lanes_to_search:
        try:
            found = connector.search(
                keywords=lane["search_keywords"][:3],
                location="San Francisco, CA",
                days_back=days_back,
            )
            postings.extend(found)
        except Exception as e:
            logger.warning("  Lane %d JobSpy failed: %s", lane["id"], e)

    logger.info("  Tier 3 total: %d postings", len(postings))
    return postings


# ── Main scan command ────────────────────────────────────────────────


def cmd_scan(args):
    """Run the daily scan."""
    db = _get_db()
    days_back = args.days
    lane_filter = args.lane

    # Skip actual search in test mode
    if os.environ.get("JOBSCAN_SKIP_SEARCH"):
        logger.info("JOBSCAN_SKIP_SEARCH set — skipping API calls")
        report_dir = _PROJECT_ROOT / "reports"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f"{date.today().isoformat()}-job-scan.md"
        md = generate_report(ranked_jobs=[], repeats=[])
        report_path.write_text(md)
        logger.info("Empty report written to %s", report_path)
        db.record_run(new_roles=0, repeat_roles=0, filtered_out=0,
                      lanes_summary={"1": 0, "2": 0, "3": 0, "4": 0})
        db.close()
        return

    # Determine which tiers to run
    # If user explicitly passes --tier flags, use only those
    # Otherwise, use .env toggles
    explicit_tiers = args.tier1 or args.tier2 or args.tier3
    if explicit_tiers:
        use_tier1 = args.tier1
        use_tier2 = args.tier2
        use_tier3 = args.tier3
    else:
        use_tier1 = _env_bool("TIER1_ENABLED")
        use_tier2 = _env_bool("TIER2_ENABLED")
        use_tier3 = _env_bool("TIER3_ENABLED")

    tier_names = []
    if use_tier1: tier_names.append("Tier1-ATS")
    if use_tier2: tier_names.append("Tier2-WebSearch")
    if use_tier3: tier_names.append("Tier3-JobSpy")
    logger.info("Active tiers: %s", ", ".join(tier_names) or "none")

    # ── Run selected tiers independently ─────────────────────────────
    all_postings: list[RawPosting] = []
    tier_counts = {}

    if use_tier1:
        t1 = run_tier1(days_back)
        tier_counts["tier1"] = len(t1)
        all_postings.extend(t1)

    if use_tier2:
        t2 = run_tier2(days_back, lane_filter)
        tier_counts["tier2"] = len(t2)
        all_postings.extend(t2)

    if use_tier3:
        t3 = run_tier3(days_back, lane_filter)
        tier_counts["tier3"] = len(t3)
        all_postings.extend(t3)

    logger.info("Total raw postings: %d (%s)",
                len(all_postings),
                ", ".join(f"{k}: {v}" for k, v in tier_counts.items()))

    # ── Dedup against database (cross-run + cross-tier) ──────────────
    new_postings = []
    repeat_count = 0
    seen_this_run: set[tuple[str, str]] = set()

    for p in all_postings:
        key = (p.company.lower().strip(), p.title.lower().strip())
        # Skip duplicates within this run (across tiers)
        if key in seen_this_run:
            continue
        seen_this_run.add(key)

        if db.is_seen(p.company, p.title):
            db.touch_job(p.company, p.title)
            repeat_count += 1
        else:
            new_postings.append(p)

    logger.info("After dedup: %d new, %d repeats, %d in-run duplicates",
                len(new_postings), repeat_count,
                len(all_postings) - len(new_postings) - repeat_count)

    # ── Hard Filter ──────────────────────────────────────────────────
    filter_result = apply_hard_filters(new_postings)
    logger.info("After hard filter: %d passed, %d filtered",
                len(filter_result.passed), len(filter_result.failed))

    survivors = filter_result.passed

    # ── --no-rank: print survivors and stop ──────────────────────────
    if getattr(args, 'no_rank', False):
        print(f"\n{'='*60}")
        print(f"Filter Results — {len(survivors)} survivors (--no-rank mode)")
        print(f"{'='*60}")
        for i, s in enumerate(survivors):
            print(f"  {i+1:>3}. {s.company} — {s.title}")
            print(f"       Location: {s.location}")
            print(f"       Source: {s.source}  |  Posted: {s.posted_date or 'unknown'}")
            print(f"       URL: {s.url}")
            print()
        print(f"Total: {len(survivors)} passed filter, {len(filter_result.failed)} filtered out")
        print(f"Run without --no-rank to proceed with LLM ranking.")
        db.close()
        return

    # ── LLM Ranking (two-pass: screen → rank) ─────────────────────────
    ranked_jobs = []
    if survivors:
        from jobscan.ranker import JobRanker
        ranker = JobRanker()
        logger.info("Screening: %s → Ranking: %s",
                     ranker.screening_model, ranker.ranking_model)
        ranked_jobs = ranker.rank_postings(survivors)

        if lane_filter:
            ranked_jobs = [j for j in ranked_jobs if j.lane == lane_filter]

        logger.info("Ranked: %d roles above threshold", len(ranked_jobs))

        for job in ranked_jobs:
            if db.is_seen(job.posting.company, job.title_clean):
                db.touch_job(job.posting.company, job.title_clean)
                continue
            db.insert_job(
                company=job.posting.company,
                title=job.title_clean,
                lane=job.lane,
                fit_score=job.fit_score,
                why_it_fits=job.why_it_fits,
                url=job.posting.url,
                location=job.posting.location,
                description=job.posting.description,
                source=job.posting.source,
            )
    elif not survivors:
        logger.info("No survivors after filtering — nothing to rank")

    # ── Generate Report ──────────────────────────────────────────────
    repeats = db.get_repeats()
    report_dir = _PROJECT_ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{date.today().isoformat()}-job-scan.md"

    md = generate_report(ranked_jobs=ranked_jobs, repeats=repeats)
    report_path.write_text(md)
    logger.info("Report written to %s", report_path)

    # ── Record run ───────────────────────────────────────────────────
    lanes_summary = {}
    for job in ranked_jobs:
        lanes_summary[str(job.lane)] = lanes_summary.get(str(job.lane), 0) + 1
    db.record_run(
        new_roles=len(ranked_jobs),
        repeat_roles=repeat_count,
        filtered_out=len(filter_result.failed),
        lanes_summary=lanes_summary,
    )

    # ── Print summary to terminal ────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Job Scan Complete — {date.today().isoformat()}")
    print(f"{'='*50}")
    print(f"Tiers used: {', '.join(tier_names)}")
    print(f"New roles found: {len(ranked_jobs)}")
    for i in range(1, 5):
        count = lanes_summary.get(str(i), 0)
        print(f"  Lane {i}: {count}")
    print(f"Repeats (still hiring): {len(repeats)}")
    print(f"Filtered out: {len(filter_result.failed)}")
    print(f"Report: {report_path}")
    print()

    db.close()


def cmd_history(args):
    """Show scan history."""
    db = _get_db()
    runs = db.get_runs()

    if not runs:
        print("No scan history yet.")
        db.close()
        return

    print(f"{'Date':<14} {'New':>5} {'Repeat':>8} {'Filtered':>10}")
    print("-" * 40)
    for run in runs[:20]:
        print(f"{run['run_date']:<14} {run['new_roles']:>5} "
              f"{run['repeat_roles']:>8} {run['filtered_out']:>10}")

    total_jobs = db.get_jobs()
    print(f"\nTotal unique jobs seen: {len(total_jobs)}")
    db.close()


def cmd_export(args):
    """Export jobs to batch_jds_auto.xlsx."""
    db = _get_db()
    kwargs = {}
    if args.lane:
        kwargs["lane"] = args.lane
    if args.status:
        kwargs["status"] = args.status
    else:
        jobs_new = db.get_jobs(status="new")
        jobs_reviewed = db.get_jobs(status="reviewed")
        all_jobs = jobs_new + jobs_reviewed
        if args.lane:
            all_jobs = [j for j in all_jobs if j["lane"] == args.lane]

        if not all_jobs:
            print("No jobs to export.")
            db.close()
            return

        job_dicts = [
            {
                "company": j["company"],
                "description": j["description"] or "",
                "url": j["url"] or "",
                "location": j["location"] or "",
            }
            for j in all_jobs
        ]

        output_path = str(_PROJECT_ROOT / "inputs" / "batch_jds_auto.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        export_to_xlsx(job_dicts, output_path)
        print(f"Exported {len(job_dicts)} jobs to {output_path}")
        db.close()
        return

    jobs = db.get_jobs(**kwargs)
    if not jobs:
        print("No jobs to export.")
        db.close()
        return

    job_dicts = [
        {
            "company": j["company"],
            "description": j["description"] or "",
            "url": j["url"] or "",
            "location": j["location"] or "",
        }
        for j in jobs
    ]

    output_path = str(_PROJECT_ROOT / "inputs" / "batch_jds_auto.xlsx")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    export_to_xlsx(job_dicts, output_path)
    print(f"Exported {len(job_dicts)} jobs to {output_path}")
    db.close()


def cmd_mark(args):
    """Mark a job's status."""
    db = _get_db()
    db.mark_status(args.company, args.title, args.status)
    print(f"Marked {args.company} — {args.title} as '{args.status}'")
    db.close()


def main():
    parser = argparse.ArgumentParser(
        prog="jobscan",
        description="Daily job scanner — find, filter, and rank job postings",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Scan options
    parser.add_argument("--lane", type=int, choices=[1, 2, 3, 4],
                        help="Scan specific lane only")
    parser.add_argument("--days", type=int, default=7,
                        help="Look back N days (default: 7)")
    parser.add_argument("--tier1", action="store_true",
                        help="Run Tier 1: Direct ATS APIs")
    parser.add_argument("--tier2", action="store_true",
                        help="Run Tier 2: Anthropic web search")
    parser.add_argument("--tier3", action="store_true",
                        help="Run Tier 3: JobSpy aggregator")
    parser.add_argument("--no-rank", action="store_true",
                        help="Stop after filtering — skip LLM ranking")

    # history
    subparsers.add_parser("history", help="Show scan history")

    # export
    export_parser = subparsers.add_parser("export", help="Export to xlsx")
    export_parser.add_argument("--lane", type=int, choices=[1, 2, 3, 4])
    export_parser.add_argument("--status", type=str)

    # mark
    mark_parser = subparsers.add_parser("mark", help="Mark job status")
    mark_parser.add_argument("company", help="Company name")
    mark_parser.add_argument("title", help="Job title")
    mark_parser.add_argument("status", choices=["new", "reviewed", "applied",
                                                  "rejected", "expired"],
                             help="New status")

    args = parser.parse_args()

    if args.command == "history":
        cmd_history(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "mark":
        cmd_mark(args)
    else:
        cmd_scan(args)


if __name__ == "__main__":
    main()
