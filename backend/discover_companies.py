"""
SYKR — Company Discovery

Discovers new companies from multiple sources and probes ATS APIs
to verify which ones have active job boards.

Sources:
  1. GitHub hiring repos (awesome lists with ATS links)
  2. YC Work at a Startup
  3. Wellfound (AngelList) company listings
  4. Cross-probe: try known company names against each ATS API

Usage:
    # Full discovery run:
    python discover_companies.py

    # Only probe existing unverified companies:
    python discover_companies.py --probe-only

    # Only scrape GitHub repos:
    python discover_companies.py --github-only

    # Dry run:
    python discover_companies.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    ATS_API_TEMPLATES,
    ATS_DOMAIN_MAP,
    GITHUB_HIRING_REPOS,
    LOG_FORMAT,
    LOG_LEVEL,
    SCRAPE_CONCURRENCY,
    SCRAPE_TIMEOUT,
    SLUG_PATTERNS,
)
import db

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredCompany:
    slug: str
    ats: str
    name: str | None = None
    careers_url: str | None = None
    source: str = ""


# ---------------------------------------------------------------------------
# Source 1: GitHub Hiring Repos
# ---------------------------------------------------------------------------

async def discover_from_github(session: aiohttp.ClientSession) -> list[DiscoveredCompany]:
    """
    Scrape GitHub README files from hiring repos.
    Extracts ATS URLs (greenhouse, lever, etc.) from markdown links.
    """
    companies: list[DiscoveredCompany] = []

    for repo in GITHUB_HIRING_REPOS:
        url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 404:
                    # Try master branch
                    url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp2:
                        if resp2.status != 200:
                            logger.warning("GitHub repo %s: neither main nor master branch found", repo)
                            continue
                        text = await resp2.text()
                elif resp.status != 200:
                    logger.warning("GitHub repo %s returned %d", repo, resp.status)
                    continue
                else:
                    text = await resp.text()

            extracted = _extract_ats_urls_from_markdown(text, source=f"github:{repo}")
            companies.extend(extracted)
            logger.info("GitHub %s: extracted %d companies", repo, len(extracted))

        except Exception as e:
            logger.error("Failed to fetch GitHub repo %s: %s", repo, e)

    return companies


def _extract_ats_urls_from_markdown(text: str, source: str) -> list[DiscoveredCompany]:
    """Extract ATS URLs from markdown content."""
    companies: list[DiscoveredCompany] = []

    # Find all URLs in markdown links: [text](url) and bare URLs
    url_pattern = re.compile(
        r'(?:'
        r'\[([^\]]*)\]\((https?://[^\s\)]+)\)'  # [name](url)
        r'|'
        r'(https?://[^\s\)\]]+)'  # bare URL
        r')'
    )

    for match in url_pattern.finditer(text):
        link_text = match.group(1) or ""
        url = match.group(2) or match.group(3) or ""
        if not url:
            continue

        # Only process URLs that match known ATS domains
        hostname = (urlparse(url).hostname or "").lower()
        ats_name: str | None = None
        for domain, ats in sorted(ATS_DOMAIN_MAP.items(), key=lambda x: -len(x[0])):
            if domain in hostname:
                ats_name = ats
                break

        if not ats_name or ats_name in ("linkedin", "wellfound"):
            continue

        # Extract slug from the URL using the same logic as seed script
        from seed_from_results import extract_slug_from_url
        extracted = extract_slug_from_url(url)
        if extracted:
            extracted.source_file = source
            # Use the markdown link text as company name if available
            if link_text and not extracted.name:
                # Clean markdown link text
                name = re.sub(r"[|\*\[\]]", "", link_text).strip()
                if name and len(name) < 100:
                    extracted.name = name

            companies.append(DiscoveredCompany(
                slug=extracted.slug,
                ats=extracted.ats,
                name=extracted.name,
                careers_url=url,
                source=source,
            ))

    return companies


# ---------------------------------------------------------------------------
# Source 2: Y Combinator (Work at a Startup)
# ---------------------------------------------------------------------------

async def discover_from_yc(session: aiohttp.ClientSession) -> list[DiscoveredCompany]:
    """
    Fetch YC company data from Work at a Startup.
    The site uses a JSON API endpoint for company listings.
    """
    companies: list[DiscoveredCompany] = []

    # YC Work at a Startup uses an Algolia-powered search
    # We try the public API endpoint
    url = "https://www.workatastartup.com/companies.json"
    alt_url = "https://www.workatastartup.com/api/companies/search"

    for try_url in [url, alt_url]:
        try:
            async with session.get(
                try_url,
                timeout=aiohttp.ClientTimeout(total=20),
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json(content_type=None)

                if isinstance(data, list):
                    company_list = data
                elif isinstance(data, dict):
                    company_list = data.get("companies", data.get("results", []))
                else:
                    continue

                for c in company_list:
                    if not isinstance(c, dict):
                        continue

                    name = c.get("name", "")
                    slug = c.get("slug", "")
                    ats_url = c.get("ats_url", "") or c.get("jobs_url", "")

                    if not name:
                        continue

                    # If we have an ATS URL, extract the company from it
                    if ats_url:
                        from seed_from_results import extract_slug_from_url, detect_ats_from_url
                        extracted = extract_slug_from_url(ats_url)
                        if extracted:
                            companies.append(DiscoveredCompany(
                                slug=extracted.slug,
                                ats=extracted.ats,
                                name=name,
                                careers_url=ats_url,
                                source="yc:workatastartup",
                            ))
                            continue

                    # Otherwise, generate a slug from the company name for later probing
                    if not slug:
                        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

                    if slug and len(slug) >= 2:
                        companies.append(DiscoveredCompany(
                            slug=slug,
                            ats="unknown",
                            name=name,
                            careers_url=f"https://www.workatastartup.com/companies/{slug}" if slug else None,
                            source="yc:workatastartup",
                        ))

                logger.info("YC Work at a Startup: found %d companies from %s", len(company_list), try_url)
                break  # Success, don't try alt URL

        except Exception as e:
            logger.warning("YC endpoint %s failed: %s", try_url, e)

    return companies


# ---------------------------------------------------------------------------
# Source 3: ATS API Probing
# ---------------------------------------------------------------------------

async def probe_company(
    session: aiohttp.ClientSession,
    slug: str,
    ats: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, str, bool, int]:
    """
    Probe an ATS API to check if a company has an active job board.
    Returns (slug, ats, is_active, job_count).
    """
    template = ATS_API_TEMPLATES.get(ats)
    if not template:
        return slug, ats, False, 0

    api_url = template.format(slug=slug)

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
                        job_count = _count_jobs_in_response(data, ats)
                        return slug, ats, True, job_count
                    except Exception:
                        # Got 200 but invalid JSON — still counts as active
                        return slug, ats, True, 0
                elif resp.status == 404:
                    return slug, ats, False, 0
                else:
                    # 429, 500, etc. — don't mark as inactive, might be transient
                    logger.debug("Probe %s/%s returned %d", ats, slug, resp.status)
                    return slug, ats, False, 0

        except asyncio.TimeoutError:
            logger.debug("Probe %s/%s timed out", ats, slug)
            return slug, ats, False, 0
        except Exception as e:
            logger.debug("Probe %s/%s error: %s", ats, slug, e)
            return slug, ats, False, 0


def _count_jobs_in_response(data: dict | list, ats: str) -> int:
    """Extract job count from an ATS API response."""
    if isinstance(data, list):
        return len(data)

    if not isinstance(data, dict):
        return 0

    # Greenhouse: { "jobs": [...] }
    if "jobs" in data and isinstance(data["jobs"], list):
        return len(data["jobs"])

    # Ashby: { "jobs": [...] }
    if "results" in data and isinstance(data["results"], list):
        return len(data["results"])

    # Workable: { "results": [...] }
    if "results" in data:
        return len(data["results"])

    # SmartRecruiters: { "content": [...] }
    if "content" in data and isinstance(data["content"], list):
        return len(data["content"])

    # Recruitee: { "offers": [...] }
    if "offers" in data and isinstance(data["offers"], list):
        return len(data["offers"])

    return 0


async def probe_unverified_companies() -> tuple[int, int]:
    """
    Probe all unverified companies that have API URLs.
    Returns (verified_count, total_probed).
    """
    companies = db.get_all_companies()
    unverified = [
        c for c in companies
        if not c.get("verified") and c.get("api_url")
    ]

    if not unverified:
        logger.info("No unverified companies with API URLs to probe")
        return 0, 0

    logger.info("Probing %d unverified companies...", len(unverified))

    semaphore = asyncio.Semaphore(SCRAPE_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=SCRAPE_CONCURRENCY)
    verified_count = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            probe_company(session, c["slug"], c["ats"], semaphore)
            for c in unverified
        ]
        results = await asyncio.gather(*tasks)

        for slug, ats, is_active, job_count in results:
            if is_active:
                # Find the company and mark as verified
                matching = [
                    c for c in unverified
                    if c["slug"] == slug and c["ats"] == ats
                ]
                for c in matching:
                    db.update_company(c["id"], {
                        "verified": True,
                        "job_count": job_count,
                    })
                    verified_count += 1

    logger.info("Verified %d / %d probed companies", verified_count, len(unverified))
    return verified_count, len(unverified)


async def cross_probe_linkedin_companies() -> int:
    """
    Take companies discovered only via LinkedIn (no ATS slug)
    and probe each major ATS to see if they have a board.
    Returns count of new ATS companies discovered.
    """
    linkedin_companies = db.get_all_companies(ats="linkedin")
    if not linkedin_companies:
        logger.info("No LinkedIn-only companies to cross-probe")
        return 0

    logger.info("Cross-probing %d LinkedIn companies against ATS APIs...", len(linkedin_companies))

    semaphore = asyncio.Semaphore(SCRAPE_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=SCRAPE_CONCURRENCY)
    discovered = 0

    # Only probe the high-volume ATS platforms
    probe_ats = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks: list[asyncio.Task] = []

        for company in linkedin_companies:
            slug = company["slug"]
            name = company.get("name")

            for ats in probe_ats:
                tasks.append(
                    asyncio.ensure_future(
                        probe_company(session, slug, ats, semaphore)
                    )
                )

        results = await asyncio.gather(*tasks)

        for slug, ats, is_active, job_count in results:
            if is_active and job_count > 0:
                # Find the original LinkedIn company for the name
                matching_linkedin = [
                    c for c in linkedin_companies if c["slug"] == slug
                ]
                name = matching_linkedin[0].get("name") if matching_linkedin else None

                api_url = ATS_API_TEMPLATES.get(ats, "").format(slug=slug)
                result = db.upsert_company(
                    slug=slug,
                    ats=ats,
                    name=name,
                    api_url=api_url,
                    source="cross_probe:linkedin",
                )
                if result:
                    db.update_company(result["id"], {
                        "verified": True,
                        "job_count": job_count,
                    })
                    discovered += 1

    logger.info("Cross-probe discovered %d new ATS companies", discovered)
    return discovered


# ---------------------------------------------------------------------------
# Main discovery pipeline
# ---------------------------------------------------------------------------

async def run_discovery(
    github: bool = True,
    yc: bool = True,
    probe: bool = True,
    cross_probe: bool = True,
    dry_run: bool = False,
) -> None:
    """Run the full company discovery pipeline."""
    run_id = None
    if not dry_run:
        run_id = db.start_scrape_run(
            source="discover_companies",
            config={
                "github": github,
                "yc": yc,
                "probe": probe,
                "cross_probe": cross_probe,
            },
        )

    total_discovered = 0
    errors = 0

    connector = aiohttp.TCPConnector(limit=SCRAPE_CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:

        # ---------------------------------------------------------------
        # Source 1: GitHub repos
        # ---------------------------------------------------------------
        if github:
            logger.info("=== Discovering from GitHub repos ===")
            github_companies = await discover_from_github(session)
            logger.info("GitHub total: %d companies", len(github_companies))

            if not dry_run:
                for c in github_companies:
                    api_url = ATS_API_TEMPLATES.get(c.ats, "").format(slug=c.slug)
                    result = db.upsert_company(
                        slug=c.slug,
                        ats=c.ats,
                        name=c.name,
                        api_url=api_url if api_url else None,
                        careers_url=c.careers_url,
                        source=c.source,
                    )
                    if result:
                        total_discovered += 1
                    else:
                        errors += 1

        # ---------------------------------------------------------------
        # Source 2: YC
        # ---------------------------------------------------------------
        if yc:
            logger.info("=== Discovering from Y Combinator ===")
            yc_companies = await discover_from_yc(session)
            logger.info("YC total: %d companies", len(yc_companies))

            if not dry_run:
                for c in yc_companies:
                    api_url = None
                    if c.ats != "unknown":
                        template = ATS_API_TEMPLATES.get(c.ats, "")
                        api_url = template.format(slug=c.slug) if template else None

                    result = db.upsert_company(
                        slug=c.slug,
                        ats=c.ats,
                        name=c.name,
                        api_url=api_url,
                        careers_url=c.careers_url,
                        source=c.source,
                    )
                    if result:
                        total_discovered += 1
                    else:
                        errors += 1

    # ---------------------------------------------------------------
    # Probe unverified companies
    # ---------------------------------------------------------------
    if probe and not dry_run:
        logger.info("=== Probing unverified companies ===")
        verified, probed = await probe_unverified_companies()
        logger.info("Probed %d, verified %d", probed, verified)

    # ---------------------------------------------------------------
    # Cross-probe LinkedIn companies
    # ---------------------------------------------------------------
    if cross_probe and not dry_run:
        logger.info("=== Cross-probing LinkedIn companies ===")
        cross_found = await cross_probe_linkedin_companies()
        total_discovered += cross_found

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    if not dry_run and run_id:
        db.finish_scrape_run(
            run_id=run_id,
            total_found=total_discovered,
            new_found=total_discovered,
            errors=errors,
            status="completed",
        )

    total_companies = db.get_company_count() if not dry_run else 0
    verified_total = len(db.get_verified_companies()) if not dry_run else 0

    logger.info("=== DISCOVERY COMPLETE ===")
    logger.info("New companies added: %d", total_discovered)
    logger.info("Total companies in DB: %d", total_companies)
    logger.info("Verified (with active boards): %d", verified_total)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SYKR Company Discovery")
    parser.add_argument("--probe-only", action="store_true", help="Only probe existing unverified companies")
    parser.add_argument("--github-only", action="store_true", help="Only scrape GitHub repos")
    parser.add_argument("--yc-only", action="store_true", help="Only scrape YC")
    parser.add_argument("--cross-probe-only", action="store_true", help="Only cross-probe LinkedIn companies")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")

    args = parser.parse_args()

    if args.probe_only:
        asyncio.run(run_discovery(github=False, yc=False, probe=True, cross_probe=False, dry_run=args.dry_run))
    elif args.github_only:
        asyncio.run(run_discovery(github=True, yc=False, probe=False, cross_probe=False, dry_run=args.dry_run))
    elif args.yc_only:
        asyncio.run(run_discovery(github=False, yc=True, probe=False, cross_probe=False, dry_run=args.dry_run))
    elif args.cross_probe_only:
        asyncio.run(run_discovery(github=False, yc=False, probe=False, cross_probe=True, dry_run=args.dry_run))
    else:
        asyncio.run(run_discovery(dry_run=args.dry_run))


if __name__ == "__main__":
    main()