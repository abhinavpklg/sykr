"""
Workable ATS Parser

API: GET https://apply.workable.com/api/v3/accounts/{slug}/jobs

Response:
{
  "results": [
    {
      "id": "abc123",
      "title": "Software Engineer",
      "shortcode": "ABC123",
      "url": "https://apply.workable.com/company/j/ABC123/",
      "shortlink": "https://apply.workable.com/company/j/ABC123/",
      "location": {
        "country": "United States",
        "countryCode": "US",
        "city": "San Francisco",
        "region": "California",
        "zipCode": "94105",
        "telecommuting": true
      },
      "department": "Engineering",
      "workplace": "remote",
      "published": "2026-02-20",
      "created": "2026-02-18"
    }
  ],
  "paging": { "next": "..." }
}
"""

from __future__ import annotations

from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Workable API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("results", data.get("jobs", []))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("title", "").strip()
        url = raw.get("url") or raw.get("shortlink", "")
        if not title or not url:
            continue

        # Build full URL if relative
        if not url.startswith("http"):
            url = f"https://apply.workable.com/{slug}/j/{raw.get('shortcode', '')}/"

        # Location
        location = _build_location(raw.get("location"))

        # Remote type — Workable has workplace field
        workplace = (raw.get("workplace") or "").lower()
        loc_data = raw.get("location") or {}
        telecommuting = loc_data.get("telecommuting", False) if isinstance(loc_data, dict) else False

        if workplace == "remote" or telecommuting:
            remote_type = "remote"
        elif workplace == "hybrid":
            remote_type = "hybrid"
        elif workplace in ("onsite", "on-site"):
            remote_type = "onsite"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Posted date
        posted_at = raw.get("published") or raw.get("created")
        if posted_at and "T" not in posted_at:
            posted_at = f"{posted_at}T00:00:00Z"

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            remote_type=remote_type,
            seniority=detect_seniority(title),
            category=raw.get("department"),
            posted_at=posted_at,
            raw_data=raw,
        ))

    return jobs


def _build_location(loc: dict[str, Any] | None) -> str | None:
    """Build location string from Workable location object."""
    if not loc or not isinstance(loc, dict):
        return None

    parts: list[str] = []
    city = loc.get("city")
    region = loc.get("region")
    country = loc.get("country")

    if city:
        parts.append(city)
    if region:
        parts.append(region)
    if country and not parts:
        parts.append(country)

    return ", ".join(parts) if parts else None