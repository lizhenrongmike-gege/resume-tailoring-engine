"""Tier 3 connector: JobSpy aggregator (Indeed, LinkedIn, Glassdoor, Google)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

from jobscan.connectors.base import BaseConnector, RawPosting

logger = logging.getLogger(__name__)


class JobSpyConnector(BaseConnector):
    """Wraps python-jobspy's scrape_jobs() into the RawPosting interface."""

    def __init__(self, sites: list[str] | None = None, results_wanted: int = 15):
        self.sites = sites or ["indeed", "linkedin", "glassdoor", "google"]
        self.results_wanted = results_wanted

        # Read optional filters from .env
        self.job_type = os.environ.get("JOBSPY_JOB_TYPE") or None
        self.distance = int(os.environ.get("JOBSPY_DISTANCE", "50"))
        self.linkedin_fetch_description = os.environ.get(
            "JOBSPY_LINKEDIN_FULL_DESC", "false"
        ).lower() in ("true", "1", "yes")
        self.description_format = os.environ.get("JOBSPY_DESC_FORMAT", "markdown")
        self.country = os.environ.get("JOBSPY_COUNTRY", "USA")

        # is_remote: empty string means no filter
        is_remote_str = os.environ.get("JOBSPY_IS_REMOTE", "")
        if is_remote_str.lower() in ("true", "1"):
            self.is_remote = True
        elif is_remote_str.lower() in ("false", "0"):
            self.is_remote = False
        else:
            self.is_remote = None

    def search(self, keywords: list[str], location: str, days_back: int = 7) -> list[RawPosting]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install -U python-jobspy")
            return []

        hours_old = days_back * 24
        all_postings: list[RawPosting] = []

        for keyword in keywords:
            try:
                logger.info("  JobSpy searching: '%s' in %s", keyword, location)

                scrape_kwargs = dict(
                    site_name=self.sites,
                    search_term=keyword,
                    location=location,
                    results_wanted=self.results_wanted,
                    hours_old=hours_old,
                    country_indeed=self.country,
                    distance=self.distance,
                    linkedin_fetch_description=self.linkedin_fetch_description,
                    description_format=self.description_format,
                )
                if self.job_type:
                    scrape_kwargs["job_type"] = self.job_type
                if self.is_remote is not None:
                    scrape_kwargs["is_remote"] = self.is_remote

                df = scrape_jobs(**scrape_kwargs)

                cutoff = datetime.now() - timedelta(days=days_back)

                for _, row in df.iterrows():
                    # Enforce date window — skip stale posts
                    posted = row.get("date_posted")
                    if posted is not None:
                        try:
                            if hasattr(posted, 'date'):
                                post_date = posted.date() if hasattr(posted.date, '__call__') else posted.date
                            else:
                                post_date = datetime.strptime(str(posted), "%Y-%m-%d").date()
                            if post_date < cutoff.date():
                                continue
                        except (ValueError, TypeError):
                            pass  # can't parse — let it through

                    description = str(row.get("description", "") or "")
                    if len(description) < 50:
                        continue

                    # Handle NaN company names
                    company = str(row.get("company", "") or "")
                    if not company or company.lower() == "nan":
                        company = ""

                    loc_parts = []
                    city = row.get("city")
                    if city and str(city).lower() != "nan":
                        loc_parts.append(str(city))
                    state = row.get("state")
                    if state and str(state).lower() != "nan":
                        loc_parts.append(str(state))
                    if row.get("is_remote") and row["is_remote"]:
                        loc_parts.append("Remote")
                    location_str = ", ".join(loc_parts) if loc_parts else str(row.get("location", ""))

                    site = str(row.get("site", "jobspy"))

                    title = str(row.get("title", "") or "")
                    if title.lower() == "nan":
                        title = ""

                    if not company and not title:
                        continue  # skip rows with no useful info

                    all_postings.append(RawPosting(
                        title=title,
                        company=company,
                        location=location_str,
                        description=description,
                        url=str(row.get("job_url", "")),
                        posted_date=str(row.get("date_posted", "")) or None,
                        source=f"jobspy-{site}",
                    ))

                logger.info("  JobSpy '%s': %d results from %s",
                            keyword, len(df), ", ".join(self.sites))

            except Exception as e:
                logger.warning("  JobSpy search failed for '%s': %s", keyword, e)
                continue

        return all_postings
