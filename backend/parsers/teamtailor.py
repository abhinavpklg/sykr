"""
Teamtailor ATS Parser

API: GET https://{slug}.teamtailor.com/api/v1/jobs
     (public embed API, no auth needed)

Response (JSON:API format):
{
  "data": [
    {
      "id": "123456",
      "type": "jobs",
      "links": { "careersite-job-url": "https://company.teamtailor.com/jobs/123-title" },
      "attributes": {
        "title": "Software Engineer",
        "body": "<p>HTML description</p>",
        "pitch": "Short pitch",
        "status": "open",
        "remote-status": "hybrid",
        "employment-type": null,
        "salary": { "min": "120000", "max": "180000", "currency": "USD" },
        "created-at": "2026-02-20T10:00:00.000+00:00",
        "tags": ["engineering"]
      },
      "relationships": {
        "department": { "data": { "id": "1", "type": "departments" } },
        "locations": { "data": [{ "id": "1", "type": "locations" }] }
      }
    }
  ],
  "included": [
    { "id": "1", "type": "departments", "attributes": { "name": "Engineering" } },
    { "id": "1", "type": "locations", "attributes": { "name": "San Francisco" } }
  ]
}
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Teamtailor JSON:API response into normalized jobs."""
    if not isinstance(data, dict):
        return []

    raw_jobs = data.get("data", [])
    if not isinstance(raw_jobs, list):
        return []

    # Build lookup for included resources (departments, locations)
    included_map = _build_included_map(data.get("included", []))

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        attrs = raw.get("attributes", {})
        if not isinstance(attrs, dict):
            continue

        title = attrs.get("title", "").strip()
        if not title:
            continue

        # URL
        links = raw.get("links", {})
        url = links.get("careersite-job-url", "")
        if not url:
            job_id = raw.get("id", "")
            url = f"https://{slug}.teamtailor.com/jobs/{job_id}"

        # Status filter
        if attrs.get("status") and attrs["status"] != "open":
            continue

        # Description
        description = _clean_html(attrs.get("body", ""))

        # Location from relationships
        location = _resolve_location(raw, included_map)

        # Salary
        salary_min, salary_max, salary_currency = _extract_salary(attrs.get("salary"))

        # Remote
        remote_status = (attrs.get("remote-status") or "").lower()
        if remote_status == "fully":
            remote_type = "remote"
        elif remote_status == "hybrid":
            remote_type = "hybrid"
        elif remote_status in ("none", "onsite"):
            remote_type = "onsite"
        else:
            remote_type = detect_remote_type(title, location, attrs)

        # Department from relationships
        category = _resolve_department(raw, included_map)

        # Tags
        tags: list[str] = attrs.get("tags", []) or []
        emp_type = attrs.get("employment-type")
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
            category=category,
            tags=tags,
            posted_at=attrs.get("created-at"),
            raw_data=raw,
        ))

    return jobs


def _build_included_map(included: list) -> dict[str, dict]:
    """Build a {type:id -> attributes} map from JSON:API included resources."""
    result: dict[str, dict] = {}
    for item in included:
        if isinstance(item, dict):
            key = f"{item.get('type')}:{item.get('id')}"
            result[key] = item.get("attributes", {})
    return result


def _resolve_location(raw: dict, included_map: dict) -> str | None:
    rels = raw.get("relationships", {})
    locations_rel = rels.get("locations", {})
    loc_data = locations_rel.get("data", [])

    if isinstance(loc_data, list):
        names: list[str] = []
        for loc in loc_data:
            if isinstance(loc, dict):
                key = f"{loc.get('type')}:{loc.get('id')}"
                attrs = included_map.get(key, {})
                name = attrs.get("name")
                if name:
                    names.append(name)
        return ", ".join(names) if names else None
    return None


def _resolve_department(raw: dict, included_map: dict) -> str | None:
    rels = raw.get("relationships", {})
    dept_rel = rels.get("department", {})
    dept_data = dept_rel.get("data")

    if isinstance(dept_data, dict):
        key = f"{dept_data.get('type')}:{dept_data.get('id')}"
        attrs = included_map.get(key, {})
        return attrs.get("name")
    return None


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