"""
Recruitee ATS Parser

API: GET https://{slug}.recruitee.com/api/offers

Response:
{
  "offers": [
    {
      "id": 123456,
      "slug": "senior-software-engineer",
      "title": "Senior Software Engineer",
      "position": 1,
      "status": "published",
      "url": "https://company.recruitee.com/o/senior-software-engineer",
      "careers_url": "https://company.recruitee.com/o/senior-software-engineer",
      "location": "San Francisco, CA",
      "city": "San Francisco",
      "country": "United States",
      "country_code": "US",
      "remote": true,
      "department": "Engineering",
      "description": "<p>HTML description</p>",
      "requirements": "<p>HTML requirements</p>",
      "min_hours": 40,
      "max_hours": 40,
      "employment_type_code": "fulltime",
      "category_code": "it",
      "experience_code": "senior",
      "education_code": null,
      "tags": ["python", "react"],
      "salary_min": 120000,
      "salary_max": 180000,
      "salary_currency": "USD",
      "salary_period": "year",
      "published_at": "2026-02-20T10:00:00.000+00:00",
      "created_at": "2026-02-18T08:00:00.000+00:00"
    }
  ]
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Recruitee API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("offers", [])
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        # Skip non-published offers
        if raw.get("status") and raw["status"] != "published":
            continue

        title = raw.get("title", "").strip()
        url = raw.get("careers_url") or raw.get("url", "")
        if not title or not url:
            continue

        if not url.startswith("http"):
            url = f"https://{slug}.recruitee.com/o/{raw.get('slug', '')}"

        # Location
        location = raw.get("location") or _build_location(raw)

        # Description
        description = _clean_html(raw.get("description", ""))

        # Salary
        salary_min = _safe_int(raw.get("salary_min"))
        salary_max = _safe_int(raw.get("salary_max"))
        salary_currency = raw.get("salary_currency", "USD") or "USD"

        # Remote
        if raw.get("remote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Seniority from experience_code or title
        seniority = _map_experience(raw.get("experience_code")) or detect_seniority(title)

        # Tags
        tags: list[str] = raw.get("tags", []) or []
        emp_type = raw.get("employment_type_code", "")
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
            seniority=seniority,
            category=raw.get("department"),
            tags=tags,
            posted_at=raw.get("published_at") or raw.get("created_at"),
            raw_data=raw,
        ))

    return jobs


def _build_location(raw: dict[str, Any]) -> str | None:
    parts: list[str] = []
    if raw.get("city"):
        parts.append(raw["city"])
    if raw.get("country"):
        parts.append(raw["country"])
    return ", ".join(parts) if parts else None


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        v = int(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _map_experience(code: str | None) -> str | None:
    if not code:
        return None
    code = code.lower()
    mapping = {
        "intern": "intern",
        "internship": "intern",
        "junior": "junior",
        "entry": "junior",
        "mid": "mid",
        "mid_senior": "senior",
        "senior": "senior",
        "lead": "senior",
        "executive": "director",
        "director": "director",
        "manager": "manager",
    }
    return mapping.get(code)


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text