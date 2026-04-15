"""Tier 2 web search discovery connector using Anthropic API."""
from __future__ import annotations

import json
import re
import logging

import requests as http_requests

from jobscan.connectors.base import BaseConnector, RawPosting

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")

DISCOVERY_SITES = [
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "ycombinator.com/jobs",
    "wellfound.com",
    "builtinsf.com",
]


def _strip_html(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


def _extract_jd_from_html(html: str, url: str) -> dict | None:
    """Extract job posting data from an HTML page.

    Priority: JSON-LD JobPosting → page text fallback.
    Returns dict with title, description, location, company, or None.
    """
    # Try JSON-LD first
    ld_pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in ld_pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "JobPosting":
                        data = item
                        break
                else:
                    continue
            if data.get("@type") == "JobPosting":
                location = ""
                loc_data = data.get("jobLocation", {})
                if isinstance(loc_data, dict):
                    addr = loc_data.get("address", {})
                    if isinstance(addr, dict):
                        location = addr.get("addressLocality", "")
                return {
                    "title": data.get("title", ""),
                    "description": _strip_html(data.get("description", "")),
                    "location": location,
                    "company": (
                        data.get("hiringOrganization", {}).get("name", "")
                        if isinstance(data.get("hiringOrganization"), dict)
                        else ""
                    ),
                }
        except (json.JSONDecodeError, AttributeError):
            continue

    # Fallback: extract text from page body
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_match:
        text = _strip_html(body_match.group(1))
        if len(text) > 50:
            h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
            title = _strip_html(h1_match.group(1)) if h1_match else ""
            return {
                "title": title,
                "description": text[:5000],
                "location": "",
                "company": "",
            }

    return None


class WebSearchConnector(BaseConnector):
    """Discovers jobs via Anthropic API web_search tool."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _build_search_queries(self, keywords: list[str], location: str) -> list[str]:
        """Build search queries combining keywords with discovery sites."""
        queries = []
        site_clause = " OR ".join(f"site:{s}" for s in DISCOVERY_SITES[:3])
        for kw in keywords:
            queries.append(f'"{kw}" ({site_clause}) {location} 2026')
        return queries

    def search(self, keywords: list[str], location: str, days_back: int = 7) -> list[RawPosting]:
        """Use Anthropic API with web_search to discover job postings."""
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed")
            return []

        client = anthropic.Anthropic(api_key=self.api_key)
        queries = self._build_search_queries(keywords, location)
        all_urls: list[dict] = []

        for query in queries:
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Search for recent job postings: {query}\n\n"
                            "Return ONLY a JSON array of objects with fields: "
                            "title, company, url. No other text."
                        ),
                    }],
                )
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text.strip()
                        json_match = re.search(r"\[.*\]", text, re.DOTALL)
                        if json_match:
                            urls = json.loads(json_match.group())
                            all_urls.extend(urls)
            except Exception as e:
                logger.warning("Web search failed for query '%s': %s", query, e)
                continue

        # Dedupe URLs
        seen_urls = set()
        unique_urls = []
        for item in all_urls:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(item)

        # Fetch each URL and extract JD
        results = []
        for item in unique_urls:
            url = item.get("url", "")
            try:
                resp = http_requests.get(url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; JobScan/1.0)"
                })
                if resp.status_code != 200:
                    continue
                extracted = _extract_jd_from_html(resp.text, url)
                if not extracted or len(extracted.get("description", "")) < 50:
                    continue
                results.append(RawPosting(
                    title=extracted.get("title") or item.get("title", ""),
                    company=extracted.get("company") or item.get("company", ""),
                    location=extracted.get("location", ""),
                    description=extracted["description"],
                    url=url,
                    posted_date=None,
                    source="websearch",
                ))
            except http_requests.RequestException as e:
                logger.warning("Failed to fetch %s: %s", url, e)
                continue

        return results
