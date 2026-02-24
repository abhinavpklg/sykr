"""
SYKR — Seed Companies from Existing Scrape Results

Reads existing JSON files (Google dorked jobs, LinkedIn jobs, ATS platforms)
and extracts company slugs from URLs to populate the companies table.

Usage:
    # From backend/ directory with .env file present:
    python seed_from_results.py --data-dir ../data

    # Or point to specific files:
    python seed_from_results.py --data-dir ../data --glob "jobs_*.json"

    # Dry run (don't write to DB):
    python seed_from_results.py --data-dir ../data --dry-run

    # Also seed jobs (not just companies):
    python seed_from_results.py --data-dir ../data --seed-jobs
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

# Load .env before importing config
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    ATS_API_TEMPLATES,
    ATS_DOMAIN_MAP,
    DATA_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    SLUG_PATTERNS,
    SlugPattern,
)
import db

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Slug extraction
# ---------------------------------------------------------------------------

@dataclass
class ExtractedCompany:
    """A company slug extracted from a job URL."""
    slug: str
    ats: str
    name: str | None = None
    careers_url: str | None = None
    source_file: str = ""


def detect_ats_from_url(url: str) -> str | None:
    """Detect the ATS platform from a URL using domain mapping."""
    parsed = urlparse(url.lower())
    hostname = parsed.hostname or ""

    # Check domain map from most specific to least specific
    # Sort by length descending so "boards.greenhouse.io" matches before "greenhouse.io"
    for domain, ats in sorted(ATS_DOMAIN_MAP.items(), key=lambda x: -len(x[0])):
        if domain in hostname:
            return ats
    return None


def extract_slug_from_url(url: str) -> ExtractedCompany | None:
    """
    Extract a company slug from a job URL.

    Examples:
        boards.greenhouse.io/stripe/jobs/123 → greenhouse:stripe
        jobs.lever.co/openai/abc123         → lever:openai
        stripe.recruitee.com/o/job-title    → recruitee:stripe
        apply.workable.com/figma/j/abc      → workable:figma
    """
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    for pattern in SLUG_PATTERNS:
        if pattern.domain_contains not in hostname:
            continue

        slug: str | None = None

        if pattern.strategy.startswith("path:"):
            idx = int(pattern.strategy.split(":")[1])
            if len(path_parts) > idx:
                slug = path_parts[idx]

        elif pattern.strategy == "subdomain":
            # e.g., stripe.recruitee.com → "stripe"
            parts = hostname.split(".")
            # Find the domain_contains portion and take what's before it
            domain_base = pattern.domain_contains.split(".")[0]
            for i, part in enumerate(parts):
                if part == domain_base:
                    if i > 0:
                        slug = parts[0]
                    break

        elif pattern.strategy.startswith("path_after:"):
            marker = pattern.strategy.split(":")[1]
            for i, part in enumerate(path_parts):
                if part.lower() == marker and i + 1 < len(path_parts):
                    slug = path_parts[i + 1]
                    break

        if slug:
            # Clean slug
            slug = clean_slug(slug)
            if slug and is_valid_slug(slug):
                return ExtractedCompany(
                    slug=slug,
                    ats=pattern.ats,
                    careers_url=url.strip(),
                )

    return None


def clean_slug(slug: str) -> str:
    """Normalize a slug: lowercase, strip whitespace, remove trailing garbage."""
    slug = slug.lower().strip()
    # Remove common URL artifacts
    slug = slug.split("?")[0]
    slug = slug.split("#")[0]
    slug = slug.rstrip("/")
    # Remove trailing /jobs, /careers, etc. that got included
    slug = re.sub(r"/(jobs|careers|openings|positions)$", "", slug)
    return slug


def is_valid_slug(slug: str) -> bool:
    """Check if an extracted slug looks like a real company slug."""
    if not slug:
        return False
    if len(slug) < 2:
        return False
    if len(slug) > 100:
        return False
    # Must be alphanumeric with hyphens/underscores (typical ATS slug format)
    if not re.match(r"^[a-z0-9][a-z0-9\-_\.]*[a-z0-9]$", slug) and len(slug) > 2:
        return False
    # Filter out common non-company slugs
    blacklist = {
        "jobs", "careers", "openings", "apply", "posting", "postings",
        "boards", "board", "api", "v0", "v1", "v2", "v3",
        "search", "results", "category", "department", "location",
        "www", "app", "help", "support", "about", "blog",
        "undefined", "null", "none", "test", "example", "demo",
    }
    if slug in blacklist:
        return False
    return True


# ---------------------------------------------------------------------------
# JSON file readers
# ---------------------------------------------------------------------------

def read_json_file(filepath: Path) -> dict | list | None:
    """Safely read and parse a JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read %s: %s", filepath, e)
        return None


def extract_from_google_results(filepath: Path) -> list[ExtractedCompany]:
    """
    Extract companies from Google dorked job results.
    Expected format: { meta: {...}, results: [{ title, url, company, platform, ... }] }
    """
    data = read_json_file(filepath)
    if not data or not isinstance(data, dict):
        return []

    results = data.get("results", [])
    companies: list[ExtractedCompany] = []

    for result in results:
        url = result.get("url", "")
        if not url:
            continue

        extracted = extract_slug_from_url(url)
        if extracted:
            # Use the company name from the result if available
            name = result.get("company")
            if name:
                extracted.name = name.strip()
            extracted.source_file = filepath.name
            companies.append(extracted)

    logger.info("Extracted %d companies from %s (%d results)", len(companies), filepath.name, len(results))
    return companies


def extract_from_linkedin_results(filepath: Path) -> list[ExtractedCompany]:
    """
    Extract companies from LinkedIn scrape results.
    These are LinkedIn jobs, so no ATS slug — but company names are useful
    for cross-referencing during discovery.

    Expected format: { meta: {...}, results: [{ title, url, company, platform, location, ... }] }
    """
    data = read_json_file(filepath)
    if not data or not isinstance(data, dict):
        return []

    results = data.get("results", [])
    companies: list[ExtractedCompany] = []

    for result in results:
        company_name = result.get("company", "").strip()
        url = result.get("url", "")
        if not company_name:
            continue

        # LinkedIn URLs don't give us ATS slugs, but we can record the company
        # name for later cross-referencing when probing ATS APIs
        slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
        if slug and is_valid_slug(slug):
            companies.append(ExtractedCompany(
                slug=slug,
                ats="linkedin",
                name=company_name,
                careers_url=url,
                source_file=filepath.name,
            ))

    logger.info("Extracted %d company names from LinkedIn file %s", len(companies), filepath.name)
    return companies


def extract_from_ats_platforms(filepath: Path) -> list[dict]:
    """
    Read ATS platform definitions.
    Expected format: { platforms: [{ name, site_query, category }] }
    Returns raw platform data for reference (not companies).
    """
    data = read_json_file(filepath)
    if not data or not isinstance(data, dict):
        return []

    platforms = data.get("platforms", [])
    logger.info("Read %d ATS platform definitions from %s", len(platforms), filepath.name)
    return platforms


# ---------------------------------------------------------------------------
# Job seeding (optional)
# ---------------------------------------------------------------------------

@dataclass
class ExtractedJob:
    """A job extracted from existing results."""
    url: str
    title: str
    ats_source: str
    company_name: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    remote_type: str | None = None
    easy_apply: bool = False
    category: str | None = None
    platform: str | None = None


def extract_jobs_from_google_results(filepath: Path) -> list[ExtractedJob]:
    """Extract job records from Google dorked results."""
    data = read_json_file(filepath)
    if not data or not isinstance(data, dict):
        return []

    results = data.get("results", [])
    jobs: list[ExtractedJob] = []

    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        if not url or not title:
            continue

        ats = detect_ats_from_url(url)
        if not ats:
            continue

        remote_type = "unknown"
        remote_search = r.get("remote_search", False)
        if remote_search or "remote" in title.lower():
            remote_type = "remote"

        jobs.append(ExtractedJob(
            url=url,
            title=title,
            ats_source=ats,
            company_name=r.get("company"),
            category=r.get("category"),
            platform=r.get("platform"),
            remote_type=remote_type,
        ))

    return jobs


def extract_jobs_from_linkedin_results(filepath: Path) -> list[ExtractedJob]:
    """Extract job records from LinkedIn results."""
    data = read_json_file(filepath)
    if not data or not isinstance(data, dict):
        return []

    results = data.get("results", [])
    jobs: list[ExtractedJob] = []

    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        if not url or not title:
            continue

        # Parse salary if present (e.g., "$120K - $180K")
        salary_min, salary_max = parse_salary(r.get("salary", ""))

        remote_type = "unknown"
        location = r.get("location", "")
        if location and "remote" in location.lower():
            remote_type = "remote"

        jobs.append(ExtractedJob(
            url=url,
            title=title,
            ats_source="linkedin",
            company_name=r.get("company"),
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            remote_type=remote_type,
            easy_apply=bool(r.get("easy_apply", False)),
            platform="linkedin",
        ))

    return jobs


def parse_salary(salary_str: str | None) -> tuple[int | None, int | None]:
    """
    Parse salary strings like "$120K - $180K", "$100,000 - $150,000".
    Returns (min, max) as integers or (None, None).
    """
    if not salary_str:
        return None, None

    # Find all dollar amounts
    amounts = re.findall(r"\$[\d,]+\.?\d*[kK]?", salary_str)
    if not amounts:
        return None, None

    parsed: list[int] = []
    for amt in amounts:
        amt = amt.replace("$", "").replace(",", "")
        if amt.lower().endswith("k"):
            parsed.append(int(float(amt[:-1]) * 1000))
        else:
            parsed.append(int(float(amt)))

    if len(parsed) >= 2:
        return min(parsed), max(parsed)
    elif len(parsed) == 1:
        return parsed[0], None
    return None, None


# ---------------------------------------------------------------------------
# Deduplication and API URL generation
# ---------------------------------------------------------------------------

def deduplicate_companies(companies: list[ExtractedCompany]) -> dict[str, ExtractedCompany]:
    """
    Deduplicate by (ats, slug) key.
    Keeps the entry with the most info (name populated, etc.).
    """
    seen: dict[str, ExtractedCompany] = {}

    for c in companies:
        key = f"{c.ats}:{c.slug}"
        if key not in seen:
            seen[key] = c
        else:
            existing = seen[key]
            # Prefer entries with a name
            if c.name and not existing.name:
                seen[key] = c

    return seen


def generate_api_url(ats: str, slug: str) -> str | None:
    """Generate the API URL for a company based on its ATS and slug."""
    template = ATS_API_TEMPLATES.get(ats)
    if template:
        return template.format(slug=slug)
    return None


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def scan_data_directory(data_dir: Path, file_glob: str = "*") -> tuple[list[Path], list[Path], list[Path]]:
    """
    Scan data directory and categorize files.
    Returns (google_files, linkedin_files, ats_files).
    """
    google_files: list[Path] = []
    linkedin_files: list[Path] = []
    ats_files: list[Path] = []

    for filepath in sorted(data_dir.glob(f"{file_glob}.json" if not file_glob.endswith(".json") else file_glob)):
        name = filepath.name.lower()
        if "linkedin" in name:
            linkedin_files.append(filepath)
        elif "ats_platform" in name:
            ats_files.append(filepath)
        elif name.endswith(".json"):
            google_files.append(filepath)

    return google_files, linkedin_files, ats_files


def seed_companies(
    data_dir: Path,
    file_glob: str = "*",
    dry_run: bool = False,
    seed_jobs: bool = False,
) -> None:
    """
    Main entry point: scan JSON files, extract companies, seed to Supabase.
    """
    google_files, linkedin_files, ats_files = scan_data_directory(data_dir, file_glob)

    logger.info("Found %d Google result files", len(google_files))
    logger.info("Found %d LinkedIn result files", len(linkedin_files))
    logger.info("Found %d ATS platform files", len(ats_files))

    if not google_files and not linkedin_files:
        logger.warning("No JSON files found in %s — nothing to seed", data_dir)
        return

    # -----------------------------------------------------------------------
    # Phase 1: Extract companies from all files
    # -----------------------------------------------------------------------
    all_companies: list[ExtractedCompany] = []

    for fp in google_files:
        all_companies.extend(extract_from_google_results(fp))

    for fp in linkedin_files:
        all_companies.extend(extract_from_linkedin_results(fp))

    logger.info("Total raw extractions: %d", len(all_companies))

    # Deduplicate
    unique = deduplicate_companies(all_companies)
    logger.info("Unique companies after dedup: %d", len(unique))

    # Split: ATS companies (have API URLs) vs LinkedIn-only (need probing later)
    ats_companies = {k: v for k, v in unique.items() if v.ats != "linkedin"}
    linkedin_companies = {k: v for k, v in unique.items() if v.ats == "linkedin"}

    logger.info("  ATS companies (with API URLs): %d", len(ats_companies))
    logger.info("  LinkedIn-only companies (need probing): %d", len(linkedin_companies))

    # Print ATS breakdown
    ats_counts: dict[str, int] = {}
    for c in ats_companies.values():
        ats_counts[c.ats] = ats_counts.get(c.ats, 0) + 1
    for ats, count in sorted(ats_counts.items(), key=lambda x: -x[1]):
        logger.info("    %s: %d", ats, count)

    if dry_run:
        logger.info("DRY RUN — not writing to database")
        _print_sample(ats_companies, linkedin_companies)
        return

    # -----------------------------------------------------------------------
    # Phase 2: Upsert ATS companies to Supabase
    # -----------------------------------------------------------------------
    run_id = db.start_scrape_run(
        source="seed_from_results",
        job_title="company seeding",
        config={"data_dir": str(data_dir), "file_glob": file_glob},
    )

    upserted = 0
    errors = 0

    for key, company in ats_companies.items():
        api_url = generate_api_url(company.ats, company.slug)
        result = db.upsert_company(
            slug=company.slug,
            ats=company.ats,
            name=company.name,
            api_url=api_url,
            careers_url=company.careers_url,
            source=f"seed:{company.source_file}",
        )
        if result:
            upserted += 1
        else:
            errors += 1

    logger.info("Upserted %d ATS companies (%d errors)", upserted, errors)

    # Also seed LinkedIn company names (marked as unverified, no API URL)
    # These will be probed by discover_companies.py later
    linkedin_upserted = 0
    for key, company in linkedin_companies.items():
        result = db.upsert_company(
            slug=company.slug,
            ats="linkedin",
            name=company.name,
            careers_url=company.careers_url,
            source=f"seed:{company.source_file}",
        )
        if result:
            linkedin_upserted += 1

    logger.info("Upserted %d LinkedIn company references", linkedin_upserted)

    # -----------------------------------------------------------------------
    # Phase 3: Optionally seed jobs
    # -----------------------------------------------------------------------
    new_jobs = 0
    if seed_jobs:
        logger.info("Seeding jobs from result files...")
        all_jobs: list[ExtractedJob] = []

        for fp in google_files:
            all_jobs.extend(extract_jobs_from_google_results(fp))
        for fp in linkedin_files:
            all_jobs.extend(extract_jobs_from_linkedin_results(fp))

        logger.info("Total jobs to seed: %d", len(all_jobs))

        for job in all_jobs:
            _, is_new = db.upsert_job(
                url=job.url,
                title=job.title,
                ats_source=job.ats_source,
                company_name=job.company_name,
                location=job.location,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                remote_type=job.remote_type,
                easy_apply=job.easy_apply,
                category=job.category,
                platform=job.platform,
            )
            if is_new:
                new_jobs += 1

        logger.info("Seeded %d new jobs", new_jobs)

    # -----------------------------------------------------------------------
    # Finish
    # -----------------------------------------------------------------------
    db.finish_scrape_run(
        run_id=run_id,
        total_found=len(ats_companies) + len(linkedin_companies),
        new_found=upserted + linkedin_upserted + new_jobs,
        errors=errors,
        status="completed",
    )

    total_companies = db.get_company_count()
    total_jobs = db.get_job_count(active_only=False)
    logger.info("=== SEED COMPLETE ===")
    logger.info("Total companies in DB: %d", total_companies)
    logger.info("Total jobs in DB: %d", total_jobs)


def _print_sample(
    ats_companies: dict[str, ExtractedCompany],
    linkedin_companies: dict[str, ExtractedCompany],
) -> None:
    """Print sample extractions for dry-run review."""
    print("\n--- Sample ATS Companies (first 20) ---")
    for i, (key, c) in enumerate(list(ats_companies.items())[:20]):
        api_url = generate_api_url(c.ats, c.slug)
        print(f"  {c.ats:18s} | {c.slug:30s} | {c.name or '':25s} | {api_url or ''}")

    print(f"\n--- Sample LinkedIn Companies (first 10) ---")
    for i, (key, c) in enumerate(list(linkedin_companies.items())[:10]):
        print(f"  {c.slug:30s} | {c.name or ''}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed SYKR companies table from existing JSON scrape results"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help=f"Directory containing JSON files (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--glob",
        type=str,
        default="*",
        help="File glob pattern (default: * matches all .json files)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and extract but don't write to database",
    )
    parser.add_argument(
        "--seed-jobs",
        action="store_true",
        help="Also seed jobs from result files (not just companies)",
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error("Data directory does not exist: %s", args.data_dir)
        sys.exit(1)

    seed_companies(
        data_dir=args.data_dir,
        file_glob=args.glob,
        dry_run=args.dry_run,
        seed_jobs=args.seed_jobs,
    )


if __name__ == "__main__":
    main()