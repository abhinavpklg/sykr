"""
Personio ATS Parser

API: GET https://{slug}.jobs.personio.de/search.json

Response:
[
  {
    "id": 123456,
    "name": "Software Engineer",
    "slug": "software-engineer-123",
    "office": "San Francisco",
    "department": "Engineering",
    "recruitingCategory": "Engineering",
    "employmentType": "permanent",
    "seniority": "experienced",
    "schedule": "full-time",
    "description": "<p>HTML</p>",
    "createdAt": "2026-02-20T10:00:00+00:00",
    "tags": ["engineering"],
    "subcompany": "Main",
    "occupationCategory": null
  }
]
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Personio API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("positions", data.get("jobs", data.get("data", [])))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = (raw.get("name") or raw.get("title", "")).strip()
        job_id = raw.get("id", "")
        if not title:
            continue

        # URL
        job_slug = raw.get("slug", "")
        if job_slug:
            url = f"https://{slug}.jobs.personio.de/job/{job_slug}"
        elif job_id:
            url = f"https://{slug}.jobs.personio.de/job/{job_id}"
        else:
            continue

        location = raw.get("office") or raw.get("location")
        description = _clean_html(raw.get("description", ""))

        # Remote
        remote_type = detect_remote_type(title, location, raw)

        # Seniority from field or title
        personio_seniority = (raw.get("seniority") or "").lower()
        seniority = _map_seniority(personio_seniority) or detect_seniority(title)

        # Tags
        tags: list[str] = raw.get("tags", []) or []
        schedule = raw.get("schedule", "")
        if schedule:
            tags.append(schedule)
        emp_type = raw.get("employmentType", "")
        if emp_type:
            tags.append(emp_type)

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            description=description,
            remote_type=remote_type,
            seniority=seniority,
            category=raw.get("department") or raw.get("recruitingCategory"),
            tags=tags,
            posted_at=raw.get("createdAt"),
            raw_data=raw,
        ))

    return jobs


def _map_seniority(s: str) -> str | None:
    mapping = {
        "student": "intern",
        "entry-level": "junior",
        "junior": "junior",
        "experienced": "mid",
        "senior": "senior",
        "lead": "senior",
        "executive": "director",
        "manager": "manager",
    }
    return mapping.get(s)


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text