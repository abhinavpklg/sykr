"""
Ashby ATS Parser

API: GET https://api.ashbyhq.com/posting-api/job-board/{slug}

Response:
{
  "jobs": [
    {
      "id": "abc-123",
      "title": "Software Engineer",
      "location": "San Francisco, CA",
      "employmentType": "FullTime",
      "department": "Engineering",
      "team": "Backend",
      "isRemote": true,
      "publishedAt": "2026-02-20T10:00:00.000Z",
      "jobUrl": "https://jobs.ashbyhq.com/company/abc-123",
      "applyUrl": "https://jobs.ashbyhq.com/company/abc-123/application",
      "descriptionHtml": "<p>HTML</p>",
      "descriptionPlain": "Plain text",
      "compensationTierSummary": "$120K – $180K",
      "locationRestrictions": [...],
      "isListed": true,
      "secondaryLocations": [...]
    }
  ]
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Ashby API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("jobs", [])
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        # Skip unlisted jobs
        if raw.get("isListed") is False:
            continue

        title = raw.get("title", "").strip()
        url = raw.get("jobUrl", "") or raw.get("applyUrl", "")
        if not title or not url:
            continue

        location = raw.get("location")
        description = raw.get("descriptionPlain", "")

        # Salary from compensationTierSummary
        salary_min, salary_max, salary_currency = _parse_compensation(
            raw.get("compensationTierSummary", "")
        )

        # Remote type — Ashby has explicit isRemote flag
        if raw.get("isRemote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Tags
        tags: list[str] = []
        employment_type = raw.get("employmentType", "")
        if employment_type:
            tags.append(employment_type)
        team = raw.get("team")
        if team:
            tags.append(team)

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
            posted_at=raw.get("publishedAt"),
            raw_data=raw,
        ))

    return jobs


def _parse_compensation(comp_str: str) -> tuple[int | None, int | None, str]:
    """Parse Ashby compensation strings like '$120K – $180K'."""
    if not comp_str:
        return None, None, "USD"

    currency = "USD"
    if "€" in comp_str:
        currency = "EUR"
    elif "£" in comp_str:
        currency = "GBP"

    amounts = re.findall(r"[\d,]+\.?\d*[kK]?", comp_str)
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