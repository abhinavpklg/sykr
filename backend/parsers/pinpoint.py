"""
Pinpoint ATS Parser

API: GET https://{slug}.pinpointhq.com/postings.json

Response:
{
  "data": [
    {
      "id": "123456",
      "type": "postings",
      "attributes": {
        "title": "Software Engineer",
        "description": "<p>HTML</p>",
        "slug": "software-engineer-123",
        "location_name": "San Francisco, CA",
        "department_name": "Engineering",
        "employment_type": "full_time",
        "remote": true,
        "published_at": "2026-02-20T10:00:00Z",
        "url": "https://company.pinpointhq.com/postings/software-engineer-123"
      }
    }
  ]
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Pinpoint API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("data", data.get("postings", []))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        # Handle JSON:API format or flat format
        attrs = raw.get("attributes", raw)
        if not isinstance(attrs, dict):
            continue

        title = attrs.get("title", "").strip()
        if not title:
            continue

        # URL
        url = attrs.get("url", "")
        if not url:
            posting_slug = attrs.get("slug", raw.get("id", ""))
            url = f"https://{slug}.pinpointhq.com/postings/{posting_slug}"

        location = attrs.get("location_name") or attrs.get("location")

        # Description
        description = _clean_html(attrs.get("description", ""))

        # Remote
        if attrs.get("remote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, attrs)

        # Tags
        tags: list[str] = []
        emp_type = attrs.get("employment_type", "")
        if emp_type:
            tags.append(emp_type.replace("_", " "))

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            description=description,
            remote_type=remote_type,
            seniority=detect_seniority(title),
            category=attrs.get("department_name") or attrs.get("department"),
            tags=tags,
            posted_at=attrs.get("published_at") or attrs.get("created_at"),
            raw_data=raw,
        ))

    return jobs


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text