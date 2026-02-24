"""
Breezy HR ATS Parser

API: GET https://{slug}.breezy.hr/json

Response: array of position objects
[
  {
    "id": "abc123",
    "name": "Software Engineer",
    "friendly_id": "senior-software-engineer",
    "url": "https://company.breezy.hr/p/abc123/senior-software-engineer",
    "location": {
      "name": "San Francisco, CA",
      "city": "San Francisco",
      "state": { "name": "California", "id": "CA" },
      "country": { "name": "United States", "id": "US" },
      "is_remote": false
    },
    "department": "Engineering",
    "type": { "name": "Full-Time", "id": "fullTime" },
    "experience": { "name": "Mid-Level", "id": "midLevel" },
    "description": "HTML description",
    "education": "Bachelors",
    "published_date": "2026-02-20T10:00:00.000Z",
    "category": { "name": "Engineering", "id": "engineering" }
  }
]
"""

from __future__ import annotations

import re
from typing import Any

from parsers import ParsedJob, detect_remote_type, detect_seniority


def parse_jobs(data: dict | list, slug: str) -> list[ParsedJob]:
    """Parse Breezy HR API response into normalized jobs."""
    if isinstance(data, dict):
        raw_jobs = data.get("positions", data.get("jobs", data.get("results", [])))
    elif isinstance(data, list):
        raw_jobs = data
    else:
        return []

    jobs: list[ParsedJob] = []

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue

        title = raw.get("name", "").strip()
        url = raw.get("url", "")
        if not title:
            continue

        if not url:
            friendly_id = raw.get("friendly_id", "")
            job_id = raw.get("id", "")
            if job_id:
                url = f"https://{slug}.breezy.hr/p/{job_id}/{friendly_id}"
        if not url:
            continue

        # Location
        location = _build_location(raw.get("location"))

        # Description
        description = _clean_html(raw.get("description", ""))

        # Remote
        loc_data = raw.get("location") or {}
        if isinstance(loc_data, dict) and loc_data.get("is_remote") is True:
            remote_type = "remote"
        else:
            remote_type = detect_remote_type(title, location, raw)

        # Seniority from experience field
        exp = raw.get("experience")
        seniority = _map_experience(exp) or detect_seniority(title)

        # Category
        cat = raw.get("category")
        category = cat.get("name") if isinstance(cat, dict) else raw.get("department")

        # Tags
        tags: list[str] = []
        job_type = raw.get("type")
        if isinstance(job_type, dict) and job_type.get("name"):
            tags.append(job_type["name"])

        jobs.append(ParsedJob(
            url=url,
            title=title,
            location=location,
            description=description,
            remote_type=remote_type,
            seniority=seniority,
            category=category,
            tags=tags,
            posted_at=raw.get("published_date"),
            raw_data=raw,
        ))

    return jobs


def _build_location(loc: Any) -> str | None:
    if isinstance(loc, str):
        return loc
    if not isinstance(loc, dict):
        return None

    # Try the name field first
    name = loc.get("name")
    if name:
        return name

    parts: list[str] = []
    if loc.get("city"):
        parts.append(loc["city"])
    state = loc.get("state")
    if isinstance(state, dict) and state.get("name"):
        parts.append(state["name"])
    elif isinstance(state, str):
        parts.append(state)
    country = loc.get("country")
    if isinstance(country, dict) and country.get("name") and not parts:
        parts.append(country["name"])

    return ", ".join(parts) if parts else None


def _map_experience(exp: Any) -> str | None:
    if not exp:
        return None
    if isinstance(exp, dict):
        exp_id = (exp.get("id") or "").lower()
    elif isinstance(exp, str):
        exp_id = exp.lower()
    else:
        return None

    mapping = {
        "intern": "intern",
        "entrylevel": "junior",
        "entry_level": "junior",
        "junior": "junior",
        "midlevel": "mid",
        "mid_level": "mid",
        "mid": "mid",
        "seniorlevel": "senior",
        "senior_level": "senior",
        "senior": "senior",
        "lead": "senior",
        "director": "director",
        "executive": "director",
        "manager": "manager",
    }
    return mapping.get(exp_id)


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text