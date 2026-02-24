"""
SYKR — Main ATS Job Scraper

Reads verified companies from Supabase, hits their ATS APIs concurrently,
parses responses, and upserts jobs with deduplication.

Supports resume on failure via a local checkpoint file.

Usage:
    python ats_scraper.py
    python ats_scraper.py --ats greenhouse
    python ats_scraper.py --company stripe --ats greenhouse
    python ats_scraper.py --dry-run
    python ats_scraper.py --limit 10
    python ats_scraper.py --resume          # resume from last failed run
    python ats_scraper.py --fresh           # ignore checkpoint, start fresh
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    BACKEND_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    SCRAPE_CONCURRENCY,
    SCRAPE_TIMEOUT,
)
import db
from parsers import ParsedJob
from parsers import greenhouse as greenhouse_parser
from parsers import lever as lever_parser
from parsers import ashby as ashby_parser
from parsers import workable as workable_parser
from parsers import smartrecruiters as smartrecruiters_parser
from parsers import recruitee as recruitee_parser
from parsers import dover as dover_parser
from parsers import breezy as breezy_parser
from parsers import bamboohr as bamboohr_parser
from parsers import teamtailor as teamtailor_parser
from parsers import pinpoint as pinpoint_parser
from parsers import rippling as rippling_parser
from parsers import personio as personio_parser
from parsers import freshteam as freshteam_parser

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------

PARSERS: dict[str, Any] = {
    "greenhouse": greenhouse_parser,
    "lever": lever_parser,
    "ashby": ashby_parser,
    "workable": workable_parser,
    "smartrecruiters": smartrecruiters_parser,
    "recruitee": recruitee_parser,
    "dover": dover_parser,
    "breezy": breezy_parser,
    "bamboohr": bamboohr_parser,
    "teamtailor": teamtailor_parser,
    "pinpoint": pinpoint_parser,
    "rippling": rippling_parser,
    "personio": personio_parser,
    "freshteam": freshteam_parser,
}

# ---------------------------------------------------------------------------
# Checkpoint for resume
# ---------------------------------------------------------------------------

CHECKPOINT_FILE = BACKEND_DIR / ".scraper_checkpoint.json"


def load_checkpoint() -> dict[str, Any]:
    """Load checkpoint from last interrupted run."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_checkpoint(data: dict[str, Any]) -> None:
    """Save checkpoint to disk."""
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(data, f)
    except OSError as e:
        logger.warning("Failed to save checkpoint: %s", e)


def clear_checkpoint() -> None:
    """Remove checkpoint file after successful run."""
    try:
        CHECKPOINT_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Scrape a single company
# ---------------------------------------------------------------------------

async def scrape_company(
    session: aiohttp.ClientSession,
    company: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> tuple[str, str, list[ParsedJob], str | None]:
    """
    Fetch and parse jobs for a single company.
    Returns (company_id, slug, parsed_jobs, error_message).
    """
    company_id: str = company["id"]
    slug: str = company["slug"]
    ats: str = company["ats"]
    api_url: str = company.get("api_url", "")

    if not api_url:
        return company_id, slug, [], "no api_url"

    parser = PARSERS.get(ats)
    if not parser:
        return company_id, slug, [], f"no parser for {ats}"

    async with semaphore:
        try:
            async with session.get(
                api_url,
                timeout=aiohttp.ClientTimeout(total=SCRAPE_TIMEOUT),
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception as e:
                        return company_id, slug, [], f"json decode error: {e}"

                    jobs = parser.parse_jobs(data, slug)
                    return company_id, slug, jobs, None

                elif resp.status == 404:
                    return company_id, slug, [], None
                elif resp.status == 429:
                    return company_id, slug, [], "rate limited (429)"
                else:
                    return company_id, slug, [], f"HTTP {resp.status}"

        except asyncio.TimeoutError:
            return company_id, slug, [], "timeout"
        except aiohttp.ClientError as e:
            return company_id, slug, [], f"connection error: {e}"
        except Exception as e:
            return company_id, slug, [], f"unexpected error: {e}"


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------

async def run_scraper(
    ats_filter: str | None = None,
    company_filter: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    resume: bool = False,
    fresh: bool = False,
) -> None:
    """Run the full scrape pipeline with resume support."""

    # Handle checkpoint
    checkpoint = load_checkpoint() if resume and not fresh else {}
    completed_ids: set[str] = set(checkpoint.get("completed_ids", []))
    run_id: str | None = checkpoint.get("run_id")
    prev_total = checkpoint.get("total_jobs", 0)
    prev_new = checkpoint.get("new_jobs", 0)
    prev_errors = checkpoint.get("errors", 0)

    if fresh:
        clear_checkpoint()
        completed_ids = set()
        run_id = None
        prev_total = 0
        prev_new = 0
        prev_errors = 0

    if completed_ids:
        logger.info("Resuming from checkpoint: %d companies already completed", len(completed_ids))

    # Fetch companies to scrape
    companies = db.get_verified_companies(ats=ats_filter)

    if company_filter:
        companies = [c for c in companies if c["slug"] == company_filter.lower()]

    if limit:
        companies = companies[:limit]

    if not companies:
        logger.warning("No companies to scrape (ats=%s, company=%s)", ats_filter, company_filter)
        return

    # Filter out already-completed companies (resume mode)
    remaining = [c for c in companies if c["id"] not in completed_ids]

    # Group by ATS for logging
    ats_counts: dict[str, int] = {}
    for c in remaining:
        ats_counts[c["ats"]] = ats_counts.get(c["ats"], 0) + 1

    logger.info(
        "Scraping %d companies (%d skipped from checkpoint) across %d ATS platforms",
        len(remaining), len(companies) - len(remaining), len(ats_counts),
    )
    for ats, count in sorted(ats_counts.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d companies", ats, count)

    # Start scrape run log (or reuse from checkpoint)
    if not dry_run and not run_id:
        run_id = db.start_scrape_run(
            source="ats_scraper",
            config={
                "ats_filter": ats_filter,
                "company_filter": company_filter,
                "company_count": len(companies),
            },
        )

    # Scrape all remaining companies concurrently
    start_time = time.monotonic()
    semaphore = asyncio.Semaphore(SCRAPE_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=SCRAPE_CONCURRENCY, limit_per_host=3)

    total_jobs = prev_total
    new_jobs = prev_new
    error_count = prev_errors
    companies_with_jobs = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            scrape_company(session, company, semaphore)
            for company in remaining
        ]
        results = await asyncio.gather(*tasks)

    # Process results — write to DB one company at a time with checkpointing
    for company_id, slug, parsed_jobs, error in results:
        if error:
            error_count += 1
            if error not in ("no api_url",) and "404" not in str(error):
                logger.warning("Error scraping %s: %s", slug, error)
            completed_ids.add(company_id)
            continue

        if not parsed_jobs:
            completed_ids.add(company_id)
            continue

        companies_with_jobs += 1
        total_jobs += len(parsed_jobs)

        # Find company info
        company_info = next((c for c in remaining if c["id"] == company_id), None)
        company_name = company_info.get("name") if company_info else None
        ats_source = company_info.get("ats", "unknown") if company_info else "unknown"

        if dry_run:
            logger.info(
                "  [DRY RUN] %s (%s): %d jobs — sample: %s",
                slug, ats_source, len(parsed_jobs),
                parsed_jobs[0].title if parsed_jobs else "N/A",
            )
            new_jobs += len(parsed_jobs)
            completed_ids.add(company_id)
            continue

        # Upsert jobs to DB
        try:
            for job in parsed_jobs:
                result, is_new = db.upsert_job(
                    url=job.url,
                    title=job.title,
                    ats_source=ats_source,
                    company_name=company_name,
                    company_id=company_id,
                    location=job.location,
                    description=job.description,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    remote_type=job.remote_type,
                    seniority=job.seniority,
                    category=job.category,
                    tags=job.tags,
                    posted_at=job.posted_at,
                    raw_data=job.raw_data,
                )
                if is_new:
                    new_jobs += 1

            # Update company metadata
            db.update_company(company_id, {
                "last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "job_count": len(parsed_jobs),
                "verified": True,
            })

            completed_ids.add(company_id)

            # Save checkpoint every 10 companies
            if len(completed_ids) % 10 == 0:
                save_checkpoint({
                    "completed_ids": list(completed_ids),
                    "run_id": run_id,
                    "total_jobs": total_jobs,
                    "new_jobs": new_jobs,
                    "errors": error_count,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(
                    "  Checkpoint: %d/%d companies done, %d new jobs so far",
                    len(completed_ids), len(companies), new_jobs,
                )

        except Exception as e:
            logger.error("Failed writing jobs for %s: %s", slug, e)
            error_count += 1
            # Save checkpoint before potentially crashing
            save_checkpoint({
                "completed_ids": list(completed_ids),
                "run_id": run_id,
                "total_jobs": total_jobs,
                "new_jobs": new_jobs,
                "errors": error_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info("Checkpoint saved. Resume with: python ats_scraper.py --resume")
            raise

    elapsed = time.monotonic() - start_time

    # Summary
    logger.info("=== SCRAPE COMPLETE ===")
    logger.info("Time: %.1fs", elapsed)
    logger.info("Companies scraped: %d / %d", companies_with_jobs, len(companies))
    logger.info("Total jobs found: %d", total_jobs)
    logger.info("New jobs: %d", new_jobs)
    logger.info("Errors: %d", error_count)

    if not dry_run:
        logger.info("Total jobs in DB: %d", db.get_job_count(active_only=False))

    # Finish scrape run log
    if run_id and not dry_run:
        db.finish_scrape_run(
            run_id=run_id,
            total_found=total_jobs,
            new_found=new_jobs,
            errors=error_count,
            status="completed",
        )

    # Clear checkpoint on success
    clear_checkpoint()
    logger.info("Checkpoint cleared — run completed successfully")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SYKR ATS Job Scraper")
    parser.add_argument("--ats", type=str, default=None, help="Scrape only this ATS")
    parser.add_argument("--company", type=str, default=None, help="Scrape only this company slug")
    parser.add_argument("--limit", type=int, default=None, help="Max companies to scrape")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse but don't write to DB")
    parser.add_argument("--resume", action="store_true", help="Resume from last interrupted run")
    parser.add_argument("--fresh", action="store_true", help="Ignore checkpoint, start fresh")

    args = parser.parse_args()

    # Auto-resume if checkpoint exists and no explicit flags
    auto_resume = not args.fresh and not args.resume and CHECKPOINT_FILE.exists()
    if auto_resume:
        logger.info("Found checkpoint from previous run. Auto-resuming (use --fresh to start over)")

    asyncio.run(run_scraper(
        ats_filter=args.ats,
        company_filter=args.company,
        limit=args.limit,
        dry_run=args.dry_run,
        resume=args.resume or auto_resume,
        fresh=args.fresh,
    ))


if __name__ == "__main__":
    main()