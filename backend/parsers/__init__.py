"""
SYKR ATS Parsers

Each parser normalizes an ATS API response into a common job schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedJob:
    """Normalized job from any ATS source."""
    url: str
    title: str
    location: str | None = None
    description: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    remote_type: str = "unknown"  # remote | onsite | hybrid | unknown
    seniority: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: str | None = None  # ISO 8601
    raw_data: dict[str, Any] = field(default_factory=dict)


def detect_remote_type(
    title: str,
    location: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Infer remote type from job title, location, and metadata."""
    text = f"{title} {location or ''}".lower()
    meta_str = str(metadata or {}).lower()

    if "hybrid" in text or "hybrid" in meta_str:
        return "hybrid"
    if "remote" in text or "remote" in meta_str:
        return "remote"
    if "on-site" in text or "onsite" in text or "in-office" in text:
        return "onsite"
    if "on-site" in meta_str or "onsite" in meta_str:
        return "onsite"
    return "unknown"


def detect_seniority(title: str) -> str | None:
    """Infer seniority level from job title."""
    t = title.lower()
    if any(k in t for k in ("intern ", "internship")):
        return "intern"
    if any(k in t for k in ("junior", "jr.", "jr ", "entry level", "entry-level", "new grad")):
        return "junior"
    if any(k in t for k in ("senior", "sr.", "sr ", "lead", "principal", "staff")):
        return "senior"
    if any(k in t for k in ("director", "vp ", "vice president", "head of", "chief")):
        return "director"
    if any(k in t for k in ("manager", "engineering manager")):
        return "manager"
    return "mid"