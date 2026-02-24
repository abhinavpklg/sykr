"""
SYKR Database Client Wrapper
All Supabase read/write operations for backend workers.
Uses service_role key — bypasses RLS (backend only, never expose to frontend).
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: Client | None = None
_request_count: int = 0
_MAX_REQUESTS_BEFORE_RESET: int = 5000


def get_client() -> Client:
    """Return a Supabase client (service_role). Resets connection periodically."""
    global _client, _request_count
    if _client is None or _request_count >= _MAX_REQUESTS_BEFORE_RESET:
        if _client is not None:
            logger.info("Resetting Supabase client after %d requests", _request_count)
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set. "
                "Create a .env file or set environment variables."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        _request_count = 0
        logger.info("Supabase client initialized for %s", SUPABASE_URL)
    _request_count += 1
    return _client


def _retry(fn, retries: int = 3, delay: float = 1.0):
    """Retry a function on connection errors."""
    import time as _time
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            err_str = str(e).lower()
            is_connection_error = any(k in err_str for k in (
                "connectionterminated", "remoteprotocolerror",
                "connectionreset", "connectionrefused", "broken pipe",
            ))
            if is_connection_error and attempt < retries - 1:
                logger.warning("Connection error (attempt %d/%d): %s", attempt + 1, retries, e)
                _time.sleep(delay * (attempt + 1))
                # Force client reset
                global _request_count
                _request_count = _MAX_REQUESTS_BEFORE_RESET
                continue
            raise


# ---------------------------------------------------------------------------
# URL Hashing (deduplication)
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication:
    - Lowercase scheme and host
    - Strip query params and fragments
    - Strip trailing slash
    - Remove www. prefix
    """
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    # Remove www. prefix
    if host.startswith("www."):
        host = host[4:]
    # Keep path, strip trailing slash
    path = parsed.path.rstrip("/")
    # Reconstruct without query/fragment
    normalized = urlunparse((scheme, host, path, "", "", ""))
    return normalized


def hash_url(url: str) -> str:
    """SHA-256 hash of the normalized URL."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

def upsert_company(
    slug: str,
    ats: str,
    name: str | None = None,
    api_url: str | None = None,
    careers_url: str | None = None,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Insert or update a company by (ats, slug) unique constraint.
    Returns the upserted row or None on error.
    """
    row: dict[str, Any] = {
        "slug": slug.lower().strip(),
        "ats": ats.lower().strip(),
    }
    if name:
        row["name"] = name.strip()
    if api_url:
        row["api_url"] = api_url.strip()
    if careers_url:
        row["careers_url"] = careers_url.strip()
    if metadata:
        row["metadata"] = metadata

    try:
        result = (
            get_client()
            .table("companies")
            .upsert(row, on_conflict="ats,slug")
            .execute()
        )
        data = result.data
        if data and len(data) > 0:
            company = data[0]
            # Append source to sources array if provided
            if source and company.get("id"):
                _append_source(company["id"], source)
            return company
        return None
    except Exception as e:
        logger.error("Failed to upsert company %s/%s: %s", ats, slug, e)
        return None


def _append_source(company_id: str, source: str) -> None:
    """Append a source tag to a company's sources array (if not already present)."""
    try:
        # Fetch current sources
        result = (
            get_client()
            .table("companies")
            .select("sources")
            .eq("id", company_id)
            .single()
            .execute()
        )
        current_sources: list[str] = result.data.get("sources", []) if result.data else []
        if source not in current_sources:
            current_sources.append(source)
            (
                get_client()
                .table("companies")
                .update({"sources": current_sources})
                .eq("id", company_id)
                .execute()
            )
    except Exception as e:
        logger.warning("Failed to append source for company %s: %s", company_id, e)


def get_verified_companies(ats: str | None = None) -> list[dict[str, Any]]:
    """Fetch all verified companies with API URLs, optionally filtered by ATS."""
    query = (
        get_client()
        .table("companies")
        .select("*")
        .eq("verified", True)
        .not_.is_("api_url", "null")
    )
    if ats:
        query = query.eq("ats", ats.lower())

    result = query.execute()
    return result.data or []


def get_all_companies(ats: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
    """Fetch all companies, optionally filtered by ATS."""
    query = get_client().table("companies").select("*").limit(limit)
    if ats:
        query = query.eq("ats", ats.lower())

    result = query.execute()
    return result.data or []


def update_company(company_id: str, updates: dict[str, Any]) -> None:
    """Update a company row by ID."""
    try:
        get_client().table("companies").update(updates).eq("id", company_id).execute()
    except Exception as e:
        logger.error("Failed to update company %s: %s", company_id, e)


def get_company_count() -> int:
    """Return total number of companies."""
    result = get_client().table("companies").select("id", count="exact").execute()
    return result.count or 0


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def upsert_job(
    url: str,
    title: str,
    ats_source: str,
    company_name: str | None = None,
    company_id: str | None = None,
    location: str | None = None,
    description: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    remote_type: str | None = None,
    seniority: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    easy_apply: bool = False,
    posted_at: str | None = None,
    raw_data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    """
    Insert or update a job by url_hash.
    Returns (job_row, is_new) tuple.
    - is_new=True if this was an INSERT (first time seeing this URL)
    - is_new=False if this was an UPDATE (already existed, refreshed last_seen)
    """
    url_h = hash_url(url)
    now = datetime.now(timezone.utc).isoformat()

    # Check if job already exists
    existing = _retry(lambda: (
        get_client()
        .table("jobs")
        .select("id")
        .eq("url_hash", url_h)
        .execute()
    ))
    is_new = not existing.data or len(existing.data) == 0

    if is_new:
        row: dict[str, Any] = {
            "url_hash": url_h,
            "url": url.strip(),
            "title": title.strip(),
            "ats_source": ats_source.lower().strip(),
            "first_seen": now,
            "last_seen": now,
            "is_active": True,
        }
        if company_name:
            row["company_name"] = company_name.strip()
        if company_id:
            row["company_id"] = company_id
        if location:
            row["location"] = location.strip()
        if description:
            # Store first 500 chars in description column
            row["description"] = description[:500].strip()
        if salary_min is not None:
            row["salary_min"] = salary_min
        if salary_max is not None:
            row["salary_max"] = salary_max
        if remote_type and remote_type in ("remote", "onsite", "hybrid", "unknown"):
            row["remote_type"] = remote_type
        if seniority:
            row["seniority"] = seniority
        if platform:
            row["platform"] = platform
        if category:
            row["category"] = category
        if tags:
            row["tags"] = tags
        if easy_apply:
            row["easy_apply"] = True
        if posted_at:
            row["posted_at"] = posted_at
        if raw_data:
            row["raw_data"] = raw_data

        try:
            result = _retry(lambda: get_client().table("jobs").insert(row).execute())
            return (result.data[0] if result.data else None, True)
        except Exception as e:
            logger.error("Failed to insert job %s: %s", url[:80], e)
            return (None, False)
    else:
        # Already exists — update last_seen and is_active
        job_id = existing.data[0]["id"]
        updates: dict[str, Any] = {
            "last_seen": now,
            "is_active": True,
        }
        # Update fields that may have changed
        if company_id:
            updates["company_id"] = company_id
        if salary_min is not None:
            updates["salary_min"] = salary_min
        if salary_max is not None:
            updates["salary_max"] = salary_max

        try:
            result = _retry(lambda: (
                get_client()
                .table("jobs")
                .update(updates)
                .eq("id", job_id)
                .execute()
            ))
            return (result.data[0] if result.data else None, False)
        except Exception as e:
            logger.error("Failed to update job %s: %s", job_id, e)
            return (None, False)


def bulk_upsert_jobs(jobs: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Upsert a batch of jobs. Each dict must have at minimum:
    url, title, ats_source.
    Returns (new_count, updated_count).
    """
    new_count = 0
    updated_count = 0
    for job in jobs:
        _, is_new = upsert_job(**job)
        if is_new:
            new_count += 1
        else:
            updated_count += 1
    return new_count, updated_count


def mark_stale_jobs(ats_source: str, active_url_hashes: set[str]) -> int:
    """
    Mark jobs as inactive if they weren't seen in the latest scrape.
    Only affects jobs from the given ATS source that were last seen > 48h ago.
    Returns count of jobs marked inactive.
    """
    cutoff = datetime.now(timezone.utc).isoformat()
    # We can't do "NOT IN" with large sets via SDK efficiently,
    # so we handle this in the scraper by tracking what we've seen.
    # This is a fallback for jobs not seen in any recent run.
    try:
        result = (
            get_client()
            .rpc("mark_stale_jobs", {
                "p_ats_source": ats_source,
                "p_hours": 48,
            })
            .execute()
        )
        return result.data if isinstance(result.data, int) else 0
    except Exception:
        # If the RPC doesn't exist yet, fall back to a simpler approach
        logger.warning("mark_stale_jobs RPC not available, skipping stale marking")
        return 0


def get_job_count(active_only: bool = True) -> int:
    """Return total number of jobs."""
    query = get_client().table("jobs").select("id", count="exact")
    if active_only:
        query = query.eq("is_active", True)
    result = query.execute()
    return result.count or 0


# ---------------------------------------------------------------------------
# Scrape Runs
# ---------------------------------------------------------------------------

def start_scrape_run(
    source: str,
    job_title: str | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """Create a new scrape_run record. Returns the run ID."""
    row: dict[str, Any] = {
        "source": source,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    if job_title:
        row["job_title"] = job_title
    if config:
        row["config"] = config

    result = get_client().table("scrape_runs").insert(row).execute()
    run_id: str = result.data[0]["id"]
    logger.info("Started scrape run %s (source=%s)", run_id, source)
    return run_id


def finish_scrape_run(
    run_id: str,
    total_found: int = 0,
    new_found: int = 0,
    errors: int = 0,
    status: str = "completed",
) -> None:
    """Mark a scrape run as finished with stats."""
    try:
        (
            get_client()
            .table("scrape_runs")
            .update({
                "total_found": total_found,
                "new_found": new_found,
                "errors": errors,
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", run_id)
            .execute()
        )
        logger.info(
            "Finished scrape run %s: total=%d new=%d errors=%d status=%s",
            run_id, total_found, new_found, errors, status,
        )
    except Exception as e:
        logger.error("Failed to finish scrape run %s: %s", run_id, e)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def delete_old_jobs(days: int = 90) -> int:
    """Delete jobs older than `days` days. Returns count deleted."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        result = (
            get_client()
            .table("jobs")
            .delete()
            .lt("first_seen", cutoff)
            .execute()
        )
        count = len(result.data) if result.data else 0
        logger.info("Deleted %d jobs older than %d days", count, days)
        return count
    except Exception as e:
        logger.error("Failed to delete old jobs: %s", e)
        return 0


def mark_inactive_jobs(hours: int = 48) -> int:
    """Mark jobs as inactive if last_seen is older than `hours` hours."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        result = (
            get_client()
            .table("jobs")
            .update({"is_active": False})
            .eq("is_active", True)
            .lt("last_seen", cutoff)
            .execute()
        )
        count = len(result.data) if result.data else 0
        logger.info("Marked %d jobs inactive (last_seen > %dh ago)", count, hours)
        return count
    except Exception as e:
        logger.error("Failed to mark inactive jobs: %s", e)
        return 0


def delete_orphaned_user_states() -> int:
    """Delete user_job_state rows where the job no longer exists."""
    # This requires a raw SQL call since SDK can't do NOT IN subquery easily.
    # For MVP, we rely on ON DELETE CASCADE on the FK — when jobs are deleted,
    # their user_job_state rows are automatically removed.
    logger.info("Orphan cleanup handled by FK CASCADE — no action needed")
    return 0