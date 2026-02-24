"""
SYKR Backend Configuration
Environment variables and constants for all backend workers.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    # Allow missing env vars only when running seed_from_results.py locally
    # with a .env file — dotenv is loaded in individual scripts if needed.
    pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_DIR: Path = Path(__file__).parent
PROJECT_ROOT: Path = BACKEND_DIR.parent
DATA_DIR: Path = PROJECT_ROOT / "data"  # where JSON result files live

# ---------------------------------------------------------------------------
# Scraper Settings
# ---------------------------------------------------------------------------

SCRAPE_CONCURRENCY: int = int(os.environ.get("SCRAPE_CONCURRENCY", "20"))
SCRAPE_TIMEOUT: int = int(os.environ.get("SCRAPE_TIMEOUT", "10"))
SCRAPE_RATE_LIMIT_PER_ATS: float = 1.0  # seconds between requests to same ATS domain

# Jobs older than this are pruned by cleanup.py
JOB_TTL_DAYS: int = 90

# Jobs not seen for this long are marked inactive
JOB_STALE_HOURS: int = 48

# ---------------------------------------------------------------------------
# ATS API URL Templates
# ---------------------------------------------------------------------------
# {slug} is replaced with the company slug at runtime.

ATS_API_TEMPLATES: dict[str, str] = {
    "greenhouse":      "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever":           "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby":           "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable":        "https://apply.workable.com/api/v3/accounts/{slug}/jobs",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
    "recruitee":       "https://{slug}.recruitee.com/api/offers",
    "dover":           "https://app.dover.com/api/careers-page/{slug}/jobs",
    "breezy":          "https://{slug}.breezy.hr/json",
    "bamboohr":        "https://{slug}.bamboohr.com/careers/list",
    "teamtailor":      "https://{slug}.teamtailor.com/api/v1/jobs",
    "pinpoint":        "https://{slug}.pinpointhq.com/postings.json",
    "rippling":        "https://ats.rippling.com/api/{slug}/jobs",
    "personio":        "https://{slug}.jobs.personio.de/search.json",
    "freshteam":       "https://{slug}.freshteam.com/api/job_postings",
}

# Maps domain substrings → ATS name (used by seed_from_results.py to detect ATS from URLs)
ATS_DOMAIN_MAP: dict[str, str] = {
    "boards.greenhouse.io":     "greenhouse",
    "boards-api.greenhouse.io": "greenhouse",
    "greenhouse.io":            "greenhouse",
    "jobs.lever.co":            "lever",
    "api.lever.co":             "lever",
    "lever.co":                 "lever",
    "jobs.ashbyhq.com":         "ashby",
    "api.ashbyhq.com":          "ashby",
    "ashbyhq.com":              "ashby",
    "apply.workable.com":       "workable",
    "workable.com":             "workable",
    "jobs.smartrecruiters.com": "smartrecruiters",
    "api.smartrecruiters.com":  "smartrecruiters",
    "smartrecruiters.com":      "smartrecruiters",
    "recruitee.com":            "recruitee",
    "dover.com":                "dover",
    "app.dover.com":            "dover",
    "breezy.hr":                "breezy",
    "bamboohr.com":             "bamboohr",
    "teamtailor.com":           "teamtailor",
    "pinpointhq.com":           "pinpoint",
    "ats.rippling.com":         "rippling",
    "rippling-ats.com":         "rippling",
    "rippling.com":             "rippling",
    "jobs.personio.de":         "personio",
    "personio.de":              "personio",
    "freshteam.com":            "freshteam",
    "wellfound.com":            "wellfound",
    "angel.co":                 "wellfound",
    "linkedin.com":             "linkedin",
}

# ---------------------------------------------------------------------------
# URL Patterns for Slug Extraction
# ---------------------------------------------------------------------------
# Each entry: (ats_name, url_contains, slug_extraction_strategy)
# Strategies:
#   "path:<n>"       → slug is the nth path segment (0-indexed)
#   "subdomain"      → slug is the leftmost subdomain
#   "path_after:<s>" → slug is the path segment immediately after string s

@dataclass
class SlugPattern:
    ats: str
    domain_contains: str
    strategy: str

SLUG_PATTERNS: list[SlugPattern] = [
    # greenhouse: boards.greenhouse.io/stripe/jobs/123 → slug = "stripe" (path segment 0)
    SlugPattern("greenhouse", "greenhouse.io", "path:0"),
    # lever: jobs.lever.co/stripe/abc123 → slug = "stripe" (path segment 0)
    SlugPattern("lever", "lever.co", "path:0"),
    # ashby: jobs.ashbyhq.com/stripe → slug = "stripe" (path segment 0)
    SlugPattern("ashby", "ashbyhq.com", "path:0"),
    # workable: apply.workable.com/stripe/ → slug = "stripe" (path segment 0)
    SlugPattern("workable", "workable.com", "path:0"),
    # smartrecruiters: jobs.smartrecruiters.com/Stripe/1234 → slug = "Stripe" (path segment 0)
    SlugPattern("smartrecruiters", "smartrecruiters.com", "path:0"),
    # recruitee: stripe.recruitee.com/o/job-title → slug = "stripe" (subdomain)
    SlugPattern("recruitee", "recruitee.com", "subdomain"),
    # dover: app.dover.com/apply/stripe/abc → slug after "apply"
    SlugPattern("dover", "dover.com", "path_after:apply"),
    # breezy: stripe.breezy.hr/p/job-title → slug = "stripe" (subdomain)
    SlugPattern("breezy", "breezy.hr", "subdomain"),
    # bamboohr: stripe.bamboohr.com/careers/123 → slug = "stripe" (subdomain)
    SlugPattern("bamboohr", "bamboohr.com", "subdomain"),
    # teamtailor: company.teamtailor.com/jobs/123 → slug = "company" (subdomain)
    SlugPattern("teamtailor", "teamtailor.com", "subdomain"),
    # pinpoint: company.pinpointhq.com/postings/123 → slug = "company" (subdomain)
    SlugPattern("pinpoint", "pinpointhq.com", "subdomain"),
    # rippling: ats.rippling.com/company/jobs/123 → slug = "company" (path segment 0)
    SlugPattern("rippling", "rippling.com", "path:0"),
    # personio: company.jobs.personio.de/job/123 → slug = "company" (subdomain)
    SlugPattern("personio", "personio.de", "subdomain"),
    # freshteam: company.freshteam.com/jobs/123 → slug = "company" (subdomain)
    SlugPattern("freshteam", "freshteam.com", "subdomain"),
]

# ---------------------------------------------------------------------------
# Discovery Sources
# ---------------------------------------------------------------------------

GITHUB_HIRING_REPOS: list[str] = [
    "poteto/hiring-without-whiteboards",
    "pittcsc/Summer2025-Internships",
    "SimplifyJobs/New-Grad-Positions",
    "remoteintech/remote-jobs",
    "tramcar/awesome-job-boards",
]

YC_COMPANIES_URL: str = "https://www.workatastartup.com/companies"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")