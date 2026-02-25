"""
Jobsekr — Performance Check

Tests Supabase query performance for common frontend operations.

Usage:
    python perf_check.py
"""

from __future__ import annotations

import time
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db
from config import LOG_FORMAT, LOG_LEVEL

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)


def time_query(name: str, fn) -> float:
    start = time.monotonic()
    fn()
    elapsed = (time.monotonic() - start) * 1000
    return elapsed


def main() -> None:
    logger.info("=== PERFORMANCE CHECK ===\n")
    client = db.get_client()

    tests: list[tuple[str, float]] = []

    # 1. Job listing page 1
    logger.info("Job Listing Queries:")

    t = time_query("Active jobs page 1", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Active jobs page 1", t))

    # 2. Search (using ilike as proxy for text_search)
    t = time_query("Search: title ilike 'react'", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .ilike("title", "%react%")
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Search 'react'", t))

    # 3. Filter: remote
    t = time_query("Filter: remote", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .eq("remote_type", "remote")
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Filter remote", t))

    # 4. Filter: ATS
    t = time_query("Filter: greenhouse", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .eq("ats_source", "greenhouse")
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Filter greenhouse", t))

    # 5. Filter: location
    t = time_query("Filter: San Francisco", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .ilike("location", "%San Francisco%")
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Filter location", t))

    # 6. Combined
    t = time_query("Combined: remote + greenhouse", lambda: (
        client.table("jobs").select("*", count="exact")
        .eq("is_active", True)
        .eq("remote_type", "remote")
        .eq("ats_source", "greenhouse")
        .order("first_seen", desc=True)
        .range(0, 29)
        .execute()
    ))
    tests.append(("Combined filters", t))

    # 7. Counts
    logger.info("\nCount Queries:")

    t = time_query("Active job count", lambda: (
        client.table("jobs").select("id", count="exact", head=True)
        .eq("is_active", True)
        .execute()
    ))
    tests.append(("Job count", t))

    t = time_query("Verified company count", lambda: (
        client.table("companies").select("id", count="exact", head=True)
        .eq("verified", True)
        .execute()
    ))
    tests.append(("Company count", t))

    # 8. Single job (modal)
    logger.info("\nSingle Record:")

    sample = client.table("jobs").select("id").eq("is_active", True).limit(1).execute()
    if sample.data:
        job_id = sample.data[0]["id"]
        t = time_query("Single job by ID", lambda: (
            client.table("jobs").select("*").eq("id", job_id).single().execute()
        ))
        tests.append(("Single job fetch", t))

    # 9. Scrape run
    t = time_query("Latest scrape run", lambda: (
        client.table("scrape_runs").select("*")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    ))
    tests.append(("Latest scrape run", t))

    # Summary
    logger.info("\n=== RESULTS ===")
    for name, ms in tests:
        if ms < 300:
            status = "✅"
        elif ms < 500:
            status = "✅"
        elif ms < 1000:
            status = "⚠️ "
        else:
            status = "❌"
        logger.info("  %s %-35s %6.0fms", status, name, ms)

    total_jobs = db.get_job_count(active_only=True)
    total_companies = db.get_company_count()
    logger.info("\n  DB size: %d active jobs, %d companies", total_jobs, total_companies)

    slow = [n for n, ms in tests if ms >= 500]
    if not slow:
        logger.info("  ✅ All queries under 500ms — PASS")
    else:
        logger.info("  ⚠️  Slow queries: %s", ", ".join(slow))


if __name__ == "__main__":
    main()