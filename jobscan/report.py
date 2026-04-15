"""Markdown report generation for daily job scan."""
from __future__ import annotations

from datetime import date

from jobscan.ranker import RankedJob
from jobscan.config import LANES

_LANE_NAMES = {lane["id"]: lane["name"] for lane in LANES}


def generate_report(ranked_jobs: list[RankedJob], repeats: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")

    by_lane: dict[int, list[RankedJob]] = {}
    for job in ranked_jobs:
        by_lane.setdefault(job.lane, []).append(job)

    lane_counts = {i: len(by_lane.get(i, [])) for i in range(1, 5)}
    total = sum(lane_counts.values())

    top_rec = ""
    if ranked_jobs:
        top = ranked_jobs[0]
        top_rec = f"{top.posting.company} — {top.title_clean}: {top.why_it_fits}"

    lines = [
        f"# Job Scan Report — {today}",
        "",
        "## Summary",
        f"- Total new roles: {total}",
        f"- Lane 1: {lane_counts[1]} | Lane 2: {lane_counts[2]} | "
        f"Lane 3: {lane_counts[3]} | Lane 4: {lane_counts[4]}",
    ]

    if top_rec:
        lines.append(f"- Top recommendation: {top_rec}")

    lines.append("")

    for lane_id in range(1, 5):
        jobs = by_lane.get(lane_id, [])
        if not jobs:
            continue

        lane_name = _LANE_NAMES.get(lane_id, f"Lane {lane_id}")
        lines.append(f"## Lane {lane_id} — {lane_name}")
        lines.append("")

        for job in jobs:
            p = job.posting
            stretch = " *(stretch)*" if job.fit_score < 66 else ""
            lines.append(f"### {p.company} — {job.title_clean}{stretch}")
            lines.append(f"- **Location:** {p.location or 'not listed'}")
            lines.append(f"- **Posted:** {p.posted_date or 'unknown'}")
            lines.append(f"- **Salary:** not listed")
            lines.append(f"- **Fit score:** {job.fit_score}/100")
            lines.append(f"- **Why it fits:** {job.why_it_fits}")
            if job.subtle_flags:
                lines.append(f"- **Flags:** {'; '.join(job.subtle_flags)}")
            lines.append(f"- **Sponsorship signal:** {job.sponsorship_signal}")
            lines.append(f"- **Apply:** [{p.url}]({p.url})")
            lines.append("")

    lines.append("## Repeats from prior runs (still hiring)")
    lines.append("")
    if repeats:
        for r in repeats:
            lines.append(
                f"- **{r['company']}** — {r['title']} "
                f"(seen {r['run_count']}x since {r['first_seen']})"
            )
    else:
        lines.append("*No repeats — first run or all roles are new.*")

    lines.append("")
    return "\n".join(lines)
