# Jobsekr — Development Tracker

**Started:** Feb 24, 2026
**Target MVP:** Mar 2, 2026
**Status:** 🟢 In Progress
**Live URL:** https://jobsekr.app

---

## Day 1 — Foundation ✅

- [x] Supabase project + schema migration
- [x] Next.js 14 app scaffolded + deployed to Vercel
- [x] Auth: email + Google OAuth, callback, session middleware
- [x] Protected routes, domain configured (jobsekr.app)

---

## Day 2 — Data Pipeline ✅

- [x] 14 ATS parsers built
- [x] Company discovery (seed, GitHub, cross-probe)
- [x] Async scraper with batch inserts, checkpoint resume, connection retry
- [x] 517 companies, 261 verified, 20,437 jobs scraped
- [x] GitHub Actions crons deployed (scrape 3×/day, discover 2×/day, cleanup 1×/day)

---

## Day 3 — Job Listing Page ✅

- [x] Job listing with filters (search, remote, ATS, location, sort)
- [x] Offset pagination with page numbers
- [x] URL-based shareable filter state

---

## Day 4 — Application Tracking + Profile ✅

- [x] Save/Apply/Hide actions on job cards
- [x] "Did you apply?" overlay flow
- [x] Dashboard with tabs (Saved/Applied/Hidden/All)
- [x] Light/dark theme system
- [x] Profile page with default filter preferences
- [x] Job detail modal with full description + copy button

---

## Day 5 — Analytics + Polish ✅

- [x] Analytics page (`/analytics`):
  - [x] Stats cards: today's applications, past month, total all-time
  - [x] Search bar for historical job applications
  - [x] Status pipeline: applied → screening → interviewing → offer / rejected / archived
  - [x] User can update job status from the analytics page
  - [x] Visual application funnel chart
- [x] `backend/cleanup.py` built
- [x] GitHub Actions crons deployed
- [x] Landing hero section with live stats + features + ATS strip
- [x] About page (`/about`)
- [x] Contact page (`/contact`) with feedback form
- [x] Persistent footer (Built by Abhinav)
- [x] Favicon + logo SVG
- [x] Logo-based Spinner component on all loading states
- [x] Keyboard navigation (/ to focus search, Escape to clear/close)
- [x] README.md
- [x] Performance check script — all queries under 500ms
- [x] E2E test checklist created

---

## Day 6 — Testing & Launch Prep (In Progress)

- [ ] Run E2E test checklist on live site
- [ ] Mobile responsive testing + fixes
- [ ] Fix any bugs found in testing
- [ ] Verify GitHub Actions scraper runs successfully with batch upsert fix
- [ ] Re-run scraper locally with raw_data for modal descriptions

---

## Day 7 — Launch

- [ ] Final bug sweep
- [ ] Launch posts:
  - [ ] Twitter/X thread
  - [ ] Reddit r/webdev, r/cscareerquestions
  - [ ] Hacker News Show HN
  - [ ] LinkedIn post
  - [ ] Indie Hackers
- [ ] Monitor:
  - [ ] Supabase dashboard (connections, storage, MAU)
  - [ ] Vercel analytics (page views, errors)
  - [ ] GitHub Actions logs (cron success/failure)
- [ ] **Checkpoint:** LIVE 🚀

---

## Metrics

| Metric | Day 1 | Current |
|---|---|---|
| Jobs in DB | 20,437 | 23,209 |
| Companies tracked | 517 | 518 |
| ATS sources live | 7 | 14 parsers (7 returning jobs) |
| Registered users | 0 | — |
| Page views | 0 | — |
| Jobs applied/saved | 0 | — |

---

## Bugs / Issues Log

| # | Description | Status | Fixed In |
|---|---|---|---|
| 1 | Supabase HTTP/2 connection drop after ~10k requests | Fixed | Day 2 — retry + client reset |
| 2 | Parser __pycache__ stale module cache | Fixed | Day 2 |
| 3 | YC Work at a Startup returns 0 (JS-rendered) | Known | Deferred |
| 4 | ESLint unused vars in dashboard/profile | Fixed | Day 4 |
| 5 | useSearchParams needs Suspense boundary | Fixed | Day 4 |
| 6 | Scraper timeout on GitHub Actions (15min) | Fixed | Day 5 — batch upsert |
| 7 | Batch insert 409 conflict on duplicate url_hash | Fixed | Day 5 — upsert with ignore_duplicates |

---

## Decisions Made

| Date | Decision | Rationale |
|---|---|---|
| Feb 24 | Built 14 ATS parsers instead of 5 | More job coverage, marginal effort per parser |
| Feb 24 | Skip YC scraping for MVP | JS-rendered, no public API |
| Feb 24 | Checkpoint resume + connection retry | Supabase HTTP/2 drops |
| Feb 24 | Offset pagination with page numbers | User preference over cursor-based |
| Feb 24 | Rebranded SYKR → Jobsekr | Domain jobsekr.app |
| Feb 24 | CSS variables for theming | Runtime theme switching |
| Feb 24 | GitHub Actions over Railway | Free for public repos |
| Feb 24 | Job detail modal instead of page | Better browse UX, kept /job/[id] for SEO |
| Feb 24 | Batch job inserts | 10x faster scraper for GitHub Actions budget |
| Feb 24 | upsert with ignore_duplicates | Eliminated 409 conflicts on batch inserts |