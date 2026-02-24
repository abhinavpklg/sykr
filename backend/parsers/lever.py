"""
Lever ATS Parser

API: GET https://api.lever.co/v0/postings/{slug}?mode=json

Response: array of posting objects
[
  {
    "id": "abc-123",
    "text": "Software Engineer",
    "hostedUrl": "https://jobs.lever.co/company/abc-123",
    "applyUrl": "https://jobs.lever.co/company/abc-123/apply",
    "categories": {
      "commitment": "Full-time",
      "department": "Engineering",
      "location": "San Francisco, CA",
      "team": "Backend"
    },
    "description": "<div>HTML description</div>",
    "descriptionPlain": "Plain text description",
    "lists": [...],
    "additional": "Additional info HTML",
    "additionalPlain": "Additional info plain",
    "salaryRange": { "min": 120000, "max": 180000, "currency": "USD", "interval": "per-year" },
    "workplaceType": "remote",
    "createdAt": 1708000000000
  }
]
"""

from __future__ import annotations

from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Lever API response into normalized jobs."""
    if isinstance(data, dict):
        # Some Lever responses wrap in an object
        raw_jobs = data.get("postings", data.get("results", []))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("text", "").strip()
        url = raw.get("hostedUrl", "")
        if not title or not url:
            continue

        categories = raw.get("categories") or {}
        location = categories.get("location")
        department = categories.get("department")
        commitment = categories.get("commitment")

        # Description
        description = raw.get("descriptionPlain", "")

        # Salary
        salary_min, salary_max, salary_currency = _extract_salary(raw)

        # Remote type — Lever has a workplaceType field
        workplace = (raw.get("workplaceType") or "").lower()
        if workplace == "remote":
            remote_type = "remote"
        elif workplace == "hybrid":
            remote_type = "hybrid"
        elif workplace in ("onsite", "on-site"):
            remote_type = "onsite"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Tags from commitment and team
        tags: list[str] = []
        if commitment:
            tags.append(commitment)
        team = categories.get("team")
        if team:
            tags.append(team)

        # Posted date (Lever uses epoch milliseconds)
        posted_at = None
        created_at = raw.get("createdAt")
        if isinstance(created_at, (int, float)) and created_at > 0:
            from datetime import datetime, timezone
            posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).isoformat()

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            description=description,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            remote_type=remote_type,
            seniority=detect_seniority(title),
            category=department,
            tags=tags,
            posted_at=posted_at,
            raw_data=raw,
        ))

    return jobs


def _extract_salary(raw: dict[str, Any]) -> tuple[int | None, int | None, str]:
    """Extract salary from Lever's salaryRange field."""
    salary_range = raw.get("salaryRange")
    if not salary_range or not isinstance(salary_range, dict):
        return None, None, "USD"

    sal_min = salary_range.get("min")
    sal_max = salary_range.get("max")
    currency = salary_range.get("currency", "USD") or "USD"

    return (
        int(sal_min) if sal_min else None,
        int(sal_max) if sal_max else None,
        currency,
    )