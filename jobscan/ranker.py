"""LLM-powered job ranking with structured profile matching.

Uses LiteLLM for model flexibility — configure via .env:
    SCREENING_MODEL=claude-haiku-4-5-20251001
    RANKING_MODEL=claude-sonnet-4-20250514
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from jobscan.connectors.base import RawPosting

logger = logging.getLogger(__name__)

_JOBSCAN_DIR = Path(__file__).parent

# Defaults
_DEFAULT_SCREENING_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_RANKING_MODEL = "claude-sonnet-4-20250514"


def _load_profile_file(filename: str) -> str:
    path = _JOBSCAN_DIR / filename
    if path.exists():
        return path.read_text()
    logger.warning("Profile file not found: %s", path)
    return ""


@dataclass
class RankedJob:
    posting: RawPosting
    lane: int
    fit_score: int
    title_clean: str
    why_it_fits: str
    disqualifiers: list[str] = field(default_factory=list)
    subtle_flags: list[str] = field(default_factory=list)
    sponsorship_signal: str = "unknown"
    preference_score: int = 0
    preference_reasons: list[str] = field(default_factory=list)


def _build_screening_prompt(postings: list[RawPosting], profile_facts: str) -> str:
    """Lightweight prompt for fast screening — just checks relevance."""
    postings_text = ""
    for i, p in enumerate(postings):
        postings_text += f"""
--- POSTING {i} ---
Title: {p.title}
Company: {p.company}
Location: {p.location}
Description (first 1500 chars):
{p.description[:1500]}
"""

    return f"""You are a job screening assistant. Quickly decide which postings are potentially relevant to this candidate.

## CANDIDATE SUMMARY
{profile_facts}

## TARGET LANES
1. Risk / Fraud / Payments / Onboarding Ops
2. Operations-linked Data Analyst (NOT product/growth/marketing analyst)
3. AI Implementation / Solutions / Technical Ops (customer-facing)
4. GTM Engineer / Revenue Ops Engineer

## HARD DISQUALIFIERS (reject immediately)
- Requires CS degree as hard requirement (not "or equivalent")
- Requires 4+ years experience
- Pure software engineering / ML research role
- Senior/Staff/Principal/Lead/Director level

## POSTINGS TO SCREEN
{postings_text}

## INSTRUCTIONS
For each posting, return a JSON array with one object per posting:
- "index": posting index (0-based)
- "dominated_lane": integer 1-4 (best-fit lane, 0 if none)
- "dominated": true if relevant to ANY of the 4 lanes, false otherwise
- "reason": one short sentence why it's relevant or not

Return ONLY the JSON array. No other text."""


def build_ranking_prompt(
    postings: list[RawPosting],
    profile_facts: str,
    profile_evidence: str,
) -> str:
    postings_text = ""
    for i, p in enumerate(postings):
        postings_text += f"""
--- POSTING {i} ---
Title: {p.title}
Company: {p.company}
Location: {p.location}
URL: {p.url}
Posted: {p.posted_date or "unknown"}
Source: {p.source}

Job Description:
{p.description[:4000]}
"""

    return f"""You are a job matching assistant. You have deep knowledge of the candidate's profile and must evaluate each job posting for fit.

## CANDIDATE PROFILE (FACTS)
{profile_facts}

## CANDIDATE EVIDENCE BY LANE
{profile_evidence}

## LANE DEFINITIONS AND MATCHING RULES

Lane 1 — Risk / Fraud / Payments / Onboarding Ops: Roles where the candidate's risk-operations evidence (see lane_1 in profile_evidence) directly translates. A strong fit (80+) means 4+ of the JD's core requirements appear in lane_1's keywords_i_can_prove with direct evidence. Moderate fit (60-79) means 2-3 keyword overlaps or transferable evidence.

Lane 2 — Operations-linked Data Analyst: Data roles attached to operations, fraud, trust, member ops, or support functions. Must use SQL + Excel/BI. NOT generic product analytics. Exclude pure product analyst, growth analyst, marketing analyst.

Lane 3 — AI Implementation / Solutions / Technical Ops: Customer-facing technical delivery of AI/software. Match against lane_3 evidence in profile_evidence (shipped multi-agent / LLM API integration work).

Lane 4 — GTM Engineer: Technical systems for sales/marketing/revenue ops. Match against lane_4 evidence in profile_evidence (outreach automation, CRM pipelines, API-driven personalization).

## SCORING RULES
- fit_score 80+: 4+ keyword overlaps with direct evidence
- fit_score 60-79: 2-3 keyword overlaps or transferable evidence
- fit_score 50-59: weak match, include only if exceptionally interesting
- fit_score < 50: exclude

## DISQUALIFIER CHECKS (flag if found)
- CS degree listed as hard requirement (not "or equivalent")
- LeetCode or algorithm interview signals
- Training foundation models or deep ML theory required
- Experience requirement > 3 years (even if phrased unusually)

## PREFERENCE SIGNALS (increase preference_score, max 5)
+1 for each: posted in last 3 days, salary visible, stack mentions matching lane tools, sponsorship-friendly signals, early/growth-stage company

## JOB POSTINGS TO EVALUATE
{postings_text}

## INSTRUCTIONS
Evaluate each posting. Return a JSON array with one object per posting. Each object must have:
- "index": posting index (0-based)
- "lane": integer 1-4 (best-fit lane)
- "fit_score": integer 0-100
- "title_clean": cleaned job title
- "why_it_fits": 1-2 sentences referencing SPECIFIC evidence from the candidate's profile
- "disqualifiers": list of strings (empty if none)
- "subtle_flags": list of notable observations
- "sponsorship_signal": "yes" / "no" / "unknown"
- "preference_score": integer 0-5
- "preference_reasons": list of reasons for preference points

Return ONLY the JSON array. No other text."""


def _parse_json_response(text: str) -> list:
    """Parse JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # drop closing fence
        text = "\n".join(lines).strip()

    result = json.loads(text)
    if not isinstance(result, list):
        result = [result]
    return result


def _llm_call(model: str, prompt: str, max_tokens: int = 4096) -> str:
    """Call any LLM via LiteLLM. Returns the text response."""
    import litellm
    litellm.suppress_debug_info = True

    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


class JobRanker:
    """Two-pass ranker: cheap model screens, strong model ranks survivors."""

    def __init__(self):
        self.screening_model = os.environ.get("SCREENING_MODEL", _DEFAULT_SCREENING_MODEL)
        self.ranking_model = os.environ.get("RANKING_MODEL", _DEFAULT_RANKING_MODEL)
        self.profile_facts = _load_profile_file("profile_facts.yaml")
        self.profile_evidence = _load_profile_file("profile_evidence.yaml")

    def _screen_batch(self, postings: list[RawPosting]) -> list[RawPosting]:
        """Pass 1: Fast screening with cheap model. Returns relevant postings."""
        prompt = _build_screening_prompt(postings, self.profile_facts)

        try:
            response_text = _llm_call(self.screening_model, prompt, max_tokens=2048)
            items = _parse_json_response(response_text)

            survivors = []
            for item in items:
                idx = item.get("index", 0)
                if idx >= len(postings):
                    continue
                if item.get("dominated", False):
                    survivors.append(postings[idx])

            return survivors

        except Exception as e:
            logger.error("Screening failed: %s — passing all through", e)
            return postings  # fail-open: pass everything to ranking

    def _rank_batch(self, postings: list[RawPosting]) -> list[RankedJob]:
        """Pass 2: Deep ranking with strong model."""
        prompt = build_ranking_prompt(postings, self.profile_facts, self.profile_evidence)

        try:
            response_text = _llm_call(self.ranking_model, prompt, max_tokens=4096)
            items = _parse_json_response(response_text)

            ranked = []
            for item in items:
                idx = item.get("index", 0)
                if idx >= len(postings):
                    continue
                score = item.get("fit_score", 0)
                if score < 50:
                    continue
                ranked.append(RankedJob(
                    posting=postings[idx],
                    lane=item.get("lane", 0),
                    fit_score=score,
                    title_clean=item.get("title_clean", postings[idx].title),
                    why_it_fits=item.get("why_it_fits", ""),
                    disqualifiers=item.get("disqualifiers", []),
                    subtle_flags=item.get("subtle_flags", []),
                    sponsorship_signal=item.get("sponsorship_signal", "unknown"),
                    preference_score=item.get("preference_score", 0),
                    preference_reasons=item.get("preference_reasons", []),
                ))
            return ranked

        except Exception as e:
            logger.error("Ranking failed for batch: %s", e)
            return []

    def rank_postings(
        self,
        postings: list[RawPosting],
        screen_batch_size: int = 20,
        rank_batch_size: int = 8,
    ) -> list[RankedJob]:
        """Two-pass ranking: screen with cheap model, rank survivors with strong model."""
        logger.info("Pass 1: Screening %d postings with %s (batches of %d)...",
                     len(postings), self.screening_model, screen_batch_size)

        # Pass 1: Screen
        screened: list[RawPosting] = []
        for i in range(0, len(postings), screen_batch_size):
            batch = postings[i : i + screen_batch_size]
            survivors = self._screen_batch(batch)
            logger.info("  Batch %d-%d: %d/%d passed screening",
                        i, i + len(batch), len(survivors), len(batch))
            screened.extend(survivors)

        logger.info("Pass 1 complete: %d/%d passed screening", len(screened), len(postings))

        if not screened:
            return []

        # Pass 2: Deep rank
        logger.info("Pass 2: Ranking %d survivors with %s (batches of %d)...",
                     len(screened), self.ranking_model, rank_batch_size)

        all_ranked: list[RankedJob] = []
        for i in range(0, len(screened), rank_batch_size):
            batch = screened[i : i + rank_batch_size]
            ranked = self._rank_batch(batch)
            logger.info("  Batch %d-%d: %d roles above threshold",
                        i, i + len(batch), len(ranked))
            all_ranked.extend(ranked)

        all_ranked.sort(key=lambda r: r.fit_score, reverse=True)
        logger.info("Pass 2 complete: %d roles above threshold", len(all_ranked))
        return all_ranked


# Backwards compatibility alias
SonnetRanker = JobRanker
