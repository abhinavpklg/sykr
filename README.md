# Jobsekr

**Every new tech job, within hours — not days.**

[jobsekr.app](https://jobsekr.app)

Jobsekr is a job aggregation platform for tech professionals. It scrapes jobs directly from 14+ ATS (Applicant Tracking System) APIs multiple times daily, deduplicates them, and presents them in a fast, searchable dashboard with application tracking.

## Why

Job searching means checking 10+ sites daily — LinkedIn, Greenhouse boards, Lever pages, Wellfound. Most aggregators are slow (days behind), incomplete, or cluttered with ads. Jobsekr pulls directly from ATS APIs so jobs appear within hours of posting.

## Features

- **14 ATS sources** — Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Dover, Breezy, BambooHR, Teamtailor, Pinpoint, Rippling, Personio, Freshteam
- **20,000+ jobs** from 500+ companies, updated 3× daily
- **Search & filter** — keyword, remote/hybrid/onsite, ATS source, location, sort
- **Application tracking** — save, apply, hide jobs with persistent state
- **Status pipeline** — applied → screening → interviewing → offered / rejected / archived
- **Analytics** — application funnel, monthly stats, searchable history
- **Dark & light themes** — system-aware with manual toggle
- **User preferences** — save default filters, auto-apply on login
- **Job detail modal** — full description from ATS, copy button
- **Shareable URLs** — every filter combination is a shareable link

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router, RSC), Tailwind CSS, TypeScript |
| Backend | Python 3.12, asyncio, aiohttp |
| Database | Supabase (PostgreSQL + Auth + RLS) |
| Hosting | Vercel (frontend), GitHub Actions (crons) |
| Domain | jobsekr.app |

## Architecture

```
Users → Next.js (Vercel) → Supabase (PostgreSQL + Auth + RLS)
                                        ↑
                          Python scrapers (GitHub Actions cron)
                          ├── discover_companies.py  (2×/day)
                          ├── ats_scraper.py          (3×/day)
                          └── cleanup.py              (1×/day)
```

- **No custom API layer** — frontend queries Supabase directly via JS SDK + RLS
- **Scrapers are stateless cron jobs** — read companies → hit ATS APIs → batch insert jobs
- **Job deduplication** by SHA-256 hash of normalized URL
- **Row Level Security** — users can only access their own data

## Project Structure

```
jobsekr/
├── frontend/                  # Next.js app → Vercel
│   ├── app/                   # Pages (App Router)
│   │   ├── page.tsx           # Landing + job listing
│   │   ├── auth/login/        # Login / signup
│   │   ├── dashboard/         # Saved/applied/hidden jobs
│   │   ├── analytics/         # Application funnel & stats
│   │   ├── profile/           # User preferences
│   │   ├── job/[id]/          # Job detail (SEO)
│   │   ├── about/             # About page
│   │   └── contact/           # Feedback form
│   ├── components/            # React components
│   └── lib/                   # Supabase clients, types, utils
├── backend/                   # Python workers → GitHub Actions
│   ├── ats_scraper.py         # Main job scraper
│   ├── discover_companies.py  # Company discovery
│   ├── cleanup.py             # Stale job pruning
│   ├── parsers/               # 14 ATS parsers
│   ├── db.py                  # Supabase client wrapper
│   └── config.py              # Config & constants
├── supabase/
│   └── migrations/            # SQL schema
└── .github/workflows/         # Cron schedules
```

## ATS Parsers

| ATS | API Endpoint | Companies |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs` | 134 |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | 59 |
| Lever | `api.lever.co/v0/postings/{slug}` | 40 |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings` | 24 |
| BambooHR | `{slug}.bamboohr.com/careers/list` | 2 |
| Recruitee | `{slug}.recruitee.com/api/offers` | 1 |
| Breezy | `{slug}.breezy.hr/json` | 1 |
| Workable | `apply.workable.com/api/v3/accounts/{slug}/jobs` | — |
| Teamtailor | `{slug}.teamtailor.com/api/v1/jobs` | — |
| Pinpoint | `{slug}.pinpointhq.com/postings.json` | — |
| Rippling | `ats.rippling.com/api/{slug}/jobs` | — |
| Personio | `{slug}.jobs.personio.de/search.json` | — |
| Freshteam | `{slug}.freshteam.com/api/job_postings` | — |
| Dover | `app.dover.com/api/careers-page/{slug}/jobs` | — |

## Local Development

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
# Fill in Supabase URL and anon key
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
# Fill in Supabase URL and service role key
pip install -r requirements.txt

# Seed companies from existing data
python seed_from_results.py --data-dir ./seed_data

# Discover + verify companies
python discover_companies.py

# Scrape jobs
python ats_scraper.py

# Cleanup stale jobs
python cleanup.py
```

### Database

Run `supabase/migrations/001_initial_schema.sql` in the Supabase SQL Editor.

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

### Backend (.env)
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

## Deployment

- **Frontend:** Auto-deploys to Vercel on push to `main`
- **Scrapers:** GitHub Actions crons (free for public repos)
  - Scrape: 3×/day (11am, 3pm, 6pm CST)
  - Discover: 2×/day (10am, 5pm CST)
  - Cleanup: 1×/day (3am CST)

## License

MIT

## Author

Built by [Abhinav](https://www.linkedin.com/in/abnav/)