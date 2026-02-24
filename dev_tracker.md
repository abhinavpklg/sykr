# SYKR — Development Tracker

**Started:** Feb 24, 2026
**Target MVP:** Mar 2, 2026
**Status:** 🟢 In Progress

---

## Day 1 — Foundation
> Goal: Supabase running, Next.js deployed, Auth working

- [x] Create Supabase project
- [x] Run schema migration (all tables + indexes + RLS policies)
- [x] Verify tables in Supabase dashboard
- [ ] Scaffold Next.js 14 app (App Router, Tailwind, TypeScript)
- [ ] Install dependencies: `@supabase/supabase-js`, `@supabase/ssr`
- [ ] Create Supabase client helpers (`lib/supabase-server.ts`, `lib/supabase-browser.ts`)
- [ ] Implement Auth: login page (email + Google OAuth)
- [ ] Implement Auth: signup, callback route, session middleware
- [ ] Protected route test: `/dashboard` redirects to `/auth/login` if not logged in
- [ ] Deploy to Vercel (connect GitHub repo)
- [ ] Set environment variables on Vercel
- [ ] **Checkpoint:** Can sign up, log in, see empty dashboard, deployed on Vercel

**Notes:**
```
Schema migration complete with all 6 tables, RLS policies, auto-profile trigger,
and updated_at triggers. Added extra indexes beyond PRD spec.
```

---

## Day 2 — Data Pipeline
> Goal: Companies in DB, first real scrape completed, Railway cron running

- [x] ~~Set up Railway project, connect GitHub repo~~ (deferred to after frontend)
- [x] Create `backend/config.py` (env vars, constants)
- [x] Create `backend/db.py` (Supabase Python client wrapper)
- [x] Port `discover_companies.py` → write to Supabase companies table
- [x] Build ATS parsers:
  - [x] `parsers/greenhouse.py`
  - [x] `parsers/lever.py`
  - [x] `parsers/ashby.py`
  - [x] `parsers/workable.py`
  - [x] `parsers/smartrecruiters.py`
  - [x] `parsers/recruitee.py`
  - [x] `parsers/dover.py`
  - [x] `parsers/breezy.py`
  - [x] `parsers/bamboohr.py`
  - [x] `parsers/teamtailor.py` (bonus)
  - [x] `parsers/pinpoint.py` (bonus)
  - [x] `parsers/rippling.py` (bonus)
  - [x] `parsers/personio.py` (bonus)
  - [x] `parsers/freshteam.py` (bonus)
- [x] Build `ats_scraper.py` (async main loop: read companies → hit APIs → write jobs)
- [x] Build `seed_from_results.py` (mine existing JSON files for company slugs)
- [x] Run discovery: seed 100+ companies from probe list
- [x] Run first scrape: verify jobs appear in Supabase jobs table
- [ ] Set up Railway cron: discovery 1x/day, scraper 3x/day
- [x] **Checkpoint:** >1000 jobs in DB from >100 companies, cron pending

**Notes:**
```
14 ATS parsers built (9 beyond PRD spec).
517 companies in DB, 261 verified with active boards.
20,437 jobs scraped on first run (target was 10k).
28 errors out of 261 companies (89% success rate).
7 ATS platforms returning jobs: Greenhouse (134), Ashby (59), Lever (40),
SmartRecruiters (24), BambooHR (2), Recruitee (1), Breezy (1).
YC source returned 0 (JS-rendered, skip for MVP).
Added connection retry + checkpoint resume to handle Supabase HTTP/2 drops.
cleanup.py still needed. Railway cron setup deferred.
```

---

## Day 3 — Job Listing Page
> Goal: Users can browse and search jobs on the live site

- [ ] Create `types.ts` (Job, Company, UserJobState types from schema)
- [ ] Build `components/Header.tsx` (logo, nav, auth state)
- [ ] Build `components/JobCard.tsx` (port design from local dashboard)
- [ ] Build `components/FilterBar.tsx` (search, remote, ATS, location, sort)
- [ ] Build `app/page.tsx` or `app/jobs/page.tsx` (Server Component, fetch jobs)
- [ ] Implement Supabase query with filters (text search, remote_type, ats_source, etc.)
- [ ] Implement pagination (cursor-based using `first_seen`)
- [ ] URL-based filter state (`/jobs?q=react&remote=true` → shareable)
- [ ] Loading skeleton while fetching
- [ ] Empty state ("No jobs match your filters")
- [ ] Deploy and test with real data
- [ ] **Checkpoint:** Can search, filter, sort, paginate jobs on live site

**Notes:**
```
```

---

## Day 4 — Application Tracking
> Goal: Logged-in users can save/apply/hide jobs, see their dashboard

- [ ] Auth middleware: protect `/dashboard` route
- [ ] Build card action buttons: Save, Applied, Hide (Client Components)
- [ ] Build `components/AppliedOverlay.tsx` (blue tint → "Applied?" → Yes/No → green)
- [ ] Wire up Supabase mutations for `user_job_state` table
- [ ] Build `app/dashboard/page.tsx`:
  - [ ] Tabs: Saved / Applied / Hidden / All
  - [ ] Same JobCard component, filtered by user state
  - [ ] Counts in tab labels
- [ ] Header counters: Viewed / Applied / Hidden (live updating)
- [ ] Clicking card body → opens URL + shows overlay (port existing behavior)
- [ ] Deploy and test full auth + tracking flow
- [ ] **Checkpoint:** Full save/apply/hide flow works, persists across sessions

**Notes:**
```
```

---

## Day 5 — Polish & More ATS
> Goal: More job coverage, better UX, production-ready

- [x] Add ATS parsers (done early — 14 total, moved to Day 2)
- [ ] Run discovery again with new parsers active
- [ ] Build `backend/cleanup.py` (delete >90 day data, mark stale jobs inactive)
- [ ] Add cleanup to Railway cron (1x/day)
- [ ] Frontend polish:
  - [ ] Loading states on all async operations
  - [ ] Error boundaries with retry buttons
  - [ ] Toast notifications for actions
  - [ ] Mobile responsive testing + fixes
  - [ ] Keyboard navigation (Enter to search, Escape to close overlays)
- [ ] SEO: page titles, meta descriptions, OG tags
- [ ] Favicon and basic branding
- [ ] **Checkpoint:** 5+ ATS live, polished UI, no console errors

**Notes:**
```
14 ATS parsers already built on Day 2. Remaining: cleanup.py, Railway cron, frontend polish.
```

---

## Day 6 — Testing & Hardening
> Goal: Everything works reliably, deployed to production

- [ ] End-to-end testing:
  - [ ] Search → filter → paginate
  - [ ] Sign up → log in → save job → mark applied → see in dashboard → log out → log in → still there
  - [ ] Overlay flow: click card → open URL → Applied? → Yes → green flash → card updates
  - [ ] Hide → switch to Hidden tab → Unhide → appears in main list
  - [ ] Filter by ATS → only that ATS shows
  - [ ] Mobile: all flows work on phone screen
- [ ] Performance checks:
  - [ ] Job listing page loads <2s
  - [ ] Search responds <500ms
  - [ ] Dashboard loads <1s
  - [ ] Check Supabase query plans, add indexes if slow
- [ ] Verify Railway crons ran successfully (check scrape_runs table)
- [ ] Set up custom domain (if purchased) on Vercel
- [ ] Error monitoring: check Vercel function logs, Supabase logs
- [ ] **Checkpoint:** All tests pass, production stable, crons verified

**Notes:**
```
```

---

## Day 7 — Launch
> Goal: Live and shared with the world

- [ ] Landing hero section: headline, subtext, screenshot, CTA
- [ ] About/FAQ section (what is this, how fresh is data, what ATS covered)
- [ ] Final bug sweep from self-testing
- [ ] README.md for the repo
- [ ] Launch posts:
  - [ ] Twitter/X thread
  - [ ] Reddit r/webdev, r/cscareerquestions
  - [ ] Hacker News Show HN
  - [ ] LinkedIn post
  - [ ] Indie Hackers
- [ ] Monitor:
  - [ ] Supabase dashboard (connections, storage, MAU)
  - [ ] Vercel analytics (page views, errors)
  - [ ] Railway logs (cron success/failure)
- [ ] **Checkpoint:** LIVE 🚀

**Notes:**
```
```

---

## Metrics After Launch

| Metric | Day 1 | Day 3 | Day 7 |
|---|---|---|---|
| Jobs in DB | 20,437 | | |
| Companies tracked | 517 | | |
| ATS sources live | 7 | | |
| Registered users | 0 | | |
| Page views | 0 | | |
| Jobs applied/saved | 0 | | |

---

## Bugs / Issues Log

| # | Description | Status | Fixed In |
|---|---|---|---|
| 1 | Supabase HTTP/2 connection drop after ~10k requests | Fixed | Day 2 — added retry + client reset in db.py |
| 2 | Parser __pycache__ stale module cache | Fixed | Day 2 — cleared pycache |
| 3 | YC Work at a Startup returns 0 (JS-rendered) | Known | Deferred — not worth headless browser for MVP |

---

## Decisions Made

| Date | Decision | Rationale |
|---|---|---|
| Feb 24 | Built 14 ATS parsers instead of 5 | Had the ATS platform list, marginal effort per parser, more job coverage |
| Feb 24 | Seed from existing JSON files before discovery | Jumpstart company registry from prior scrape work |
| Feb 24 | Skip YC scraping for MVP | JS-rendered page, no public JSON API, GitHub repos provide similar coverage |
| Feb 24 | Added checkpoint resume to scraper | First run hit HTTP/2 connection limit, needed crash recovery |
| Feb 24 | Keep ATS templates in config.py, not DB | Only used at discovery time, 14 platforms rarely change, simpler for MVP |