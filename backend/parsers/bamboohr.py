"""
BambooHR ATS Parser

API: GET https://{slug}.bamboohr.com/careers/list

Response (JSON when Accept: application/json header is sent):
{
  "result": [
    {
      "id": "123",
      "jobOpeningName": "Software Engineer",
      "departmentLabel": "Engineering",
      "locationLabel": "San Francisco, CA",
      "employmentStatusLabel": "Full-Time",
      "jobOpeningUrl": "/careers/123",
      "isRemote": "yes"
    }
  ]
}

Alternative response format (some companies):
{
  "result": {
    "jobOpenings": [
      { ... same fields ... }
    ]
  }
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse BambooHR API response into normalized jobs."""
    raw_jobs: list[dict] = []

    if isinstance(data, dict):
        result = data.get("result", data)
        if isinstance(result, list):
            raw_jobs = result
        elif isinstance(result, dict):
            raw_jobs = result.get("jobOpenings", result.get("jobs", []))
    elif isinstance(data, list):
        raw_jobs = data

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = (raw.get("jobOpeningName") or raw.get("title", "")).strip()
        job_id = raw.get("id", "")
        if not title or not job_id:
            continue

        # Build URL
        job_path = raw.get("jobOpeningUrl", "")
        if job_path and job_path.startswith("http"):
            url = job_path
        elif job_path:
            url = f"https://{slug}.bamboohr.com{job_path}"
        else:
            url = f"https://{slug}.bamboohr.com/careers/{job_id}"

        location = raw.get("locationLabel") or raw.get("location")

        # Remote
        is_remote = raw.get("isRemote", "").lower() in ("yes", "true", "1")
        if is_remote:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Tags
        tags: list[str] = []
        emp_status = raw.get("employmentStatusLabel", "")
        if emp_status:
            tags.append(emp_status)

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            remote_type=remote_type,
            seniority=detect_seniority(title),
            category=raw.get("departmentLabel") or raw.get("department"),
            tags=tags,
            raw_data=raw,
        ))

    return jobs