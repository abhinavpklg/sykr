"""
SmartRecruiters ATS Parser

API: GET https://api.smartrecruiters.com/v1/companies/{slug}/postings

Response:
{
  "totalFound": 42,
  "offset": 0,
  "limit": 100,
  "content": [
    {
      "id": "abc-123",
      "uuid": "abc-123-uuid",
      "name": "Software Engineer",
      "releasedDate": "2026-02-20T10:00:00.000Z",
      "location": {
        "city": "San Francisco",
        "region": "California",
        "country": "US",
        "remote": true
      },
      "department": { "label": "Engineering" },
      "experienceLevel": { "label": "Mid-Senior level" },
      "typeOfEmployment": { "label": "Full-time" },
      "ref": "https://api.smartrecruiters.com/v1/companies/company/postings/abc-123",
      "company": { "name": "Company", "identifier": "company" },
      "customField": [...]
    }
  ]
}
"""

from __future__ import annotations

from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse SmartRecruiters API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("content", [])
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("name", "").strip()
        job_id = raw.get("id") or raw.get("uuid", "")
        if not title or not job_id:
            continue

        url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"

        # Location
        location = _build_location(raw.get("location"))

        # Remote type
        loc_data = raw.get("location") or {}
        is_remote = loc_data.get("remote", False) if isinstance(loc_data, dict) else False
        if is_remote:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Department
        dept = raw.get("department")
        category = dept.get("label") if isinstance(dept, dict) else None

        # Experience level → seniority
        exp_level = raw.get("experienceLevel")
        seniority_raw = exp_level.get("label", "") if isinstance(exp_level, dict) else ""
        seniority = _map_seniority(seniority_raw) or detect_seniority(title)

        # Tags from employment type
        tags: list[str] = []
        emp_type = raw.get("typeOfEmployment")
        if isinstance(emp_type, dict) and emp_type.get("label"):
            tags.append(emp_type["label"])

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            remote_type=remote_type,
            seniority=seniority,
            category=category,
            tags=tags,
            posted_at=raw.get("releasedDate"),
            raw_data=raw,
        ))

    return jobs


def _build_location(loc: dict[str, Any] | None) -> str | None:
    """Build location string from SmartRecruiters location object."""
    if not loc or not isinstance(loc, dict):
        return None

    parts: list[str] = []
    city = loc.get("city")
    region = loc.get("region")
    country = loc.get("country")

    if city:
        parts.append(city)
    if region:
        parts.append(region)
    if country and not parts:
        parts.append(country)

    return ", ".join(parts) if parts else None


def _map_seniority(label: str) -> str | None:
    """Map SmartRecruiters experience level labels to our seniority values."""
    label_lower = label.lower()
    if "intern" in label_lower:
        return "intern"
    if "entry" in label_lower or "junior" in label_lower:
        return "junior"
    if "mid" in label_lower:
        return "mid"
    if "senior" in label_lower or "lead" in label_lower:
        return "senior"
    if "director" in label_lower or "executive" in label_lower or "vp" in label_lower:
        return "director"
    if "manager" in label_lower:
        return "manager"
    return None