"""
Dover ATS Parser

API: GET https://app.dover.com/api/careers-page/{slug}/jobs

Response: array of job objects
[
  {
    "id": "abc-123",
    "title": "Software Engineer",
    "location": "San Francisco, CA",
    "department": "Engineering",
    "is_remote": true,
    "employment_type": "Full-time",
    "url": "https://app.dover.com/apply/company/abc-123",
    "description": "Plain text or HTML description",
    "published_date": "2026-02-20T10:00:00Z",
    "salary": { "min": 120000, "max": 180000, "currency": "USD" }
  }
]

Note: Dover's API format may vary. This parser handles known variants.
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Dover API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("jobs", data.get("results", []))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("title", "").strip()
        job_id = raw.get("id", "")
        url = raw.get("url", "")
        if not title:
            continue

        if not url and job_id:
            url = f"https://app.dover.com/apply/{slug}/{job_id}"
        if not url:
            continue

        location = raw.get("location")
        description = _clean_html(raw.get("description", ""))

        # Salary
        salary_min, salary_max, salary_currency = _extract_salary(raw)

        # Remote
        if raw.get("is_remote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Tags
        tags: list[str] = []
        emp_type = raw.get("employment_type", "")
        if emp_type:
            tags.append(emp_type)

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
            posted_at=raw.get("published_date") or raw.get("created_at"),
            raw_data=raw,
        ))

    return jobs


def _extract_salary(raw: dict[str, Any]) -> tuple[int | None, int | None, str]:
    salary = raw.get("salary")
    if isinstance(salary, dict):
        sal_min = salary.get("min")
        sal_max = salary.get("max")
        currency = salary.get("currency", "USD") or "USD"
        return (
            int(sal_min) if sal_min else None,
            int(sal_max) if sal_max else None,
            currency,
        )
    # Sometimes salary is a string
    if isinstance(salary, str):
        return _parse_salary_string(salary)
    return None, None, "USD"


def _parse_salary_string(s: str) -> tuple[int | None, int | None, str]:
    currency = "USD"
    if "€" in s:
        currency = "EUR"
    elif "£" in s:
        currency = "GBP"

    amounts = re.findall(r"[\d,]+\.?\d*[kK]?", s)
    parsed: list[int] = []
    for amt in amounts:
        amt = amt.replace(",", "")
        if amt.lower().endswith("k"):
            parsed.append(int(float(amt[:-1]) * 1000))
        else:
            val = float(amt)
            if val > 0:
                parsed.append(int(val))

    if len(parsed) >= 2:
        return min(parsed), max(parsed), currency
    elif len(parsed) == 1:
        return parsed[0], None, currency
    return None, None, currency


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text