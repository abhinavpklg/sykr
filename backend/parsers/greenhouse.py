"""
Greenhouse ATS Parser

API: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
Optional: ?content=true for full descriptions

Response:
{
  "jobs": [
    {
      "id": 123456,
      "title": "Software Engineer",
      "absolute_url": "https://boards.greenhouse.io/company/jobs/123456",
      "location": { "name": "San Francisco, CA" },
      "updated_at": "2026-02-20T10:00:00-05:00",
      "metadata": [...],
      "departments": [{ "name": "Engineering" }],
      "content": "<p>Job description HTML...</p>"  (if ?content=true)
    }
  ],
  "meta": { "total": 42 }
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Greenhouse API response into normalized jobs."""
    if isinstance(data, list):
        raw_jobs = data
    elif isinstance(data, dict):
        raw_jobs = data.get("jobs", [])
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("title", "").strip()
        url = raw.get("absolute_url", "")
        if not title or not url:
            continue

        location_obj = raw.get("location") or {}
        location = location_obj.get("name") if isinstance(location_obj, dict) else None

        # Description (available if ?content=true was used)
        description = _clean_html(raw.get("content", ""))

        # Salary from metadata
        salary_min, salary_max, salary_currency = _extract_salary(raw.get("metadata", []))

        # Remote type
        remote_type = detect_remote_type(title, location, raw)

        # Category from departments
        departments = raw.get("departments", [])
        category = departments[0].get("name") if departments and isinstance(departments[0], dict) else None

        # Posted date
        posted_at = raw.get("updated_at")

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
            posted_at=posted_at,
            raw_data=raw,
        ))

    return jobs


def _extract_salary(metadata: list[dict[str, Any]]) -> tuple[int | None, int | None, str]:
    """Extract salary from Greenhouse metadata field."""
    if not metadata or not isinstance(metadata, list):
        return None, None, "USD"

    for item in metadata:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").lower()
        value = item.get("value") or ""

        if "salary" in name or "compensation" in name:
            return _parse_salary_string(str(value))

    return None, None, "USD"


def _parse_salary_string(s: str) -> tuple[int | None, int | None, str]:
    """Parse salary strings like '$120,000 - $180,000' or '$120K-$180K'."""
    currency = "USD"
    if "€" in s or "eur" in s.lower():
        currency = "EUR"
    elif "£" in s or "gbp" in s.lower():
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
    """Strip HTML tags for plain text description."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text