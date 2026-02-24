"""
Freshteam ATS Parser

API: GET https://{slug}.freshteam.com/api/job_postings

Response:
[
  {
    "id": 123456,
    "title": "Software Engineer",
    "description": "<p>HTML</p>",
    "status": "published",
    "remote": true,
    "branch": { "name": "San Francisco", "city": "San Francisco", "state": "CA", "country": "US" },
    "department": { "name": "Engineering" },
    "type": "full_time",
    "experience": "5-8 years",
    "salary": { "min": 120000, "max": 180000, "currency": "USD" },
    "created_at": "2026-02-20T10:00:00Z",
    "updated_at": "2026-02-21T10:00:00Z",
    "closing_date": null
  }
]
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Freshteam API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("job_postings", data.get("jobs", data.get("data", [])))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        # Skip non-published
        if raw.get("status") and raw["status"] != "published":
            continue

        title = raw.get("title", "").strip()
        job_id = raw.get("id", "")
        if not title:
            continue

        url = f"https://{slug}.freshteam.com/jobs/{job_id}"

        # Location
        location = _build_location(raw.get("branch"))

        # Description
        description = _clean_html(raw.get("description", ""))

        # Salary
        salary_min, salary_max, salary_currency = _extract_salary(raw.get("salary"))

        # Remote
        if raw.get("remote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Category
        dept = raw.get("department")
        category = dept.get("name") if isinstance(dept, dict) else None

        # Tags
        tags: list[str] = []
        job_type = raw.get("type", "")
        if job_type:
            tags.append(job_type.replace("_", " ").title())

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
            category=category,
            tags=tags,
            posted_at=raw.get("created_at"),
            raw_data=raw,
        ))

    return jobs


def _build_location(branch: Any) -> str | None:
    if not branch or not isinstance(branch, dict):
        return None

    name = branch.get("name")
    if name:
        return name

    parts: list[str] = []
    if branch.get("city"):
        parts.append(branch["city"])
    if branch.get("state"):
        parts.append(branch["state"])
    if branch.get("country") and not parts:
        parts.append(branch["country"])

    return ", ".join(parts) if parts else None


def _extract_salary(salary: Any) -> tuple[int | None, int | None, str]:
    if not salary or not isinstance(salary, dict):
        return None, None, "USD"

    sal_min = salary.get("min")
    sal_max = salary.get("max")
    currency = salary.get("currency", "USD") or "USD"

    return (
        int(float(sal_min)) if sal_min else None,
        int(float(sal_max)) if sal_max else None,
        currency,
    )


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text