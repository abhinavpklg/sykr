"""
Rippling ATS Parser

API: GET https://ats.rippling.com/api/{slug}/jobs

Response:
[
  {
    "id": "abc-123",
    "title": "Software Engineer",
    "slug": "software-engineer",
    "department": "Engineering",
    "location": "San Francisco, CA",
    "workplaceType": "REMOTE",
    "employmentType": "FULL_TIME",
    "description": "<p>HTML</p>",
    "compensationRange": {
      "min": 120000,
      "max": 180000,
      "currency": "USD",
      "interval": "ANNUAL"
    },
    "publishedAt": "2026-02-20T10:00:00Z",
    "url": "https://ats.rippling.com/company/jobs/abc-123"
  }
]
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Rippling ATS API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("jobs", data.get("data", data.get("results", [])))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("title", "").strip()
        if not title:
            continue

        # URL
        url = raw.get("url", "")
        if not url:
            job_id = raw.get("id") or raw.get("slug", "")
            url = f"https://ats.rippling.com/{slug}/jobs/{job_id}"

        location = raw.get("location")
        description = _clean_html(raw.get("description", ""))

        # Salary
        salary_min, salary_max, salary_currency = _extract_salary(raw.get("compensationRange"))

        # Remote
        workplace = (raw.get("workplaceType") or "").upper()
        if workplace == "REMOTE":
            remote_type = "remote"
        elif workplace == "HYBRID":
            remote_type = "hybrid"
        elif workplace in ("ONSITE", "ON_SITE", "IN_OFFICE"):
            remote_type = "onsite"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Tags
        tags: list[str] = []
        emp_type = raw.get("employmentType", "")
        if emp_type:
            tags.append(emp_type.replace("_", " ").title())

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
            category=raw.get("department"),
            tags=tags,
            posted_at=raw.get("publishedAt") or raw.get("created_at"),
            raw_data=raw,
        ))

    return jobs


def _extract_salary(comp: Any) -> tuple[int | None, int | None, str]:
    if not comp or not isinstance(comp, dict):
        return None, None, "USD"

    sal_min = comp.get("min")
    sal_max = comp.get("max")
    currency = comp.get("currency", "USD") or "USD"

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