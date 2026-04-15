#!/usr/bin/env python3
"""One-time script to discover and verify ATS slugs for priority companies."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobscan.config import PRIORITY_COMPANIES
from jobscan.connectors.greenhouse import GreenhouseConnector
from jobscan.connectors.lever import LeverConnector
from jobscan.connectors.ashby import AshbyConnector

gh = GreenhouseConnector()
lv = LeverConnector()
ab = AshbyConnector()


def try_all_ats(name: str, slug: str) -> str | None:
    """Try each ATS provider and return the one that works."""
    # Try Greenhouse
    results = gh.fetch_company(slug, name, days_back=365)
    if results is not None and results != []:
        return "greenhouse"
    time.sleep(0.5)

    # Try Lever
    results = lv.fetch_company(slug, name, days_back=365)
    if results is not None and results != []:
        return "lever"
    time.sleep(0.5)

    # Try Ashby
    results = ab.fetch_company(slug, name, days_back=365)
    if results is not None and results != []:
        return "ashby"
    time.sleep(0.5)

    return None


if __name__ == "__main__":
    print(f"Discovering ATS slugs for {len(PRIORITY_COMPANIES)} companies...\n")

    for co in PRIORITY_COMPANIES:
        if co["ats"] != "unknown":
            # Verify known ATS
            connector = {"greenhouse": gh, "lever": lv, "ashby": ab}.get(co["ats"])
            if connector:
                results = connector.fetch_company(co["slug"], co["name"], days_back=365)
                status = f"✓ {co['ats']}/{co['slug']} ({len(results)} jobs)" if results else f"✗ {co['ats']}/{co['slug']} (no results — slug may be wrong)"
                print(f"  {co['name']}: {status}")
                time.sleep(0.5)
        else:
            # Try to discover
            found = try_all_ats(co["name"], co["slug"])
            if found:
                print(f"  {co['name']}: DISCOVERED → {found}/{co['slug']}")
            else:
                # Try alternate slugs
                alt_slugs = [
                    co["slug"].replace(".", ""),
                    co["slug"].replace("-", ""),
                    co["name"].lower().replace(" ", "").replace(".", ""),
                ]
                for alt in alt_slugs:
                    found = try_all_ats(co["name"], alt)
                    if found:
                        print(f"  {co['name']}: DISCOVERED → {found}/{alt}")
                        break
                else:
                    print(f"  {co['name']}: NOT FOUND on any ATS")
