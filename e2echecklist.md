# Jobsekr — End-to-End Test Checklist

Run through on https://jobsekr.app (both desktop and mobile)

## 1. Landing Page
- [ ] Hero section loads with live job/company counts
- [ ] "Start tracking for free" CTA links to /auth/login
- [ ] "Browse jobs" scrolls to job listing
- [ ] Feature cards and ATS strip render correctly
- [ ] Hero disappears when filters are applied

## 2. Job Listing
- [ ] Jobs load on page — grid of cards visible
- [ ] **Search:** type "react" → press Enter → filtered results
- [ ] **Search clear:** press Escape → search clears
- [ ] **Search shortcut:** press `/` → search input focuses
- [ ] **Remote filter:** select "Remote" → only remote jobs
- [ ] **ATS filter:** select "Greenhouse" → only Greenhouse jobs
- [ ] **Location filter:** select "United States" → location-filtered
- [ ] **Sort:** switch to "Oldest first" → order reverses
- [ ] **Pagination:** click page 2 → new results, page number highlighted
- [ ] **URL state:** filters appear in URL → copy URL → paste in new tab → same results
- [ ] **Empty state:** search gibberish → "No jobs match your filters" message
- [ ] **Job count:** counter in filter bar updates with each filter

## 3. Job Detail Modal
- [ ] Click any job card → modal opens with blurred backdrop
- [ ] Title, company, location, badges render correctly
- [ ] Full description loads (check a Greenhouse or Lever job)
- [ ] "Copy description" button works → paste in notepad to verify
- [ ] "Apply on [ATS]" button opens correct URL in new tab
- [ ] Press Escape → modal closes
- [ ] Click backdrop (outside modal) → modal closes
- [ ] Body scroll is locked while modal is open

## 4. Authentication
- [ ] Go to /auth/login → login page renders
- [ ] **Sign up** with email/password → "Check your email" message
- [ ] **Sign in** with email/password → redirects to home
- [ ] **Google OAuth:** "Continue with Google" → Google flow → redirected back
- [ ] **Protected routes:** logged out → go to /dashboard → redirected to login
- [ ] **Protected routes:** logged out → go to /analytics → redirected to login
- [ ] **Protected routes:** logged out → go to /profile → redirected to login
- [ ] **Sign out:** click "Sign out" in header → redirected to home, auth state cleared

## 5. Application Tracking (requires login)
- [ ] Job cards show Save / Applied? / Hide buttons
- [ ] **Save:** click Save → button turns blue "Saved"
- [ ] **Unsave:** click Saved again → reverts to "Save"
- [ ] **Applied overlay:** click job card → opens URL → shows "Did you apply?" overlay
- [ ] **Applied Yes:** click Yes → green flash → "✓ Applied" badge on card
- [ ] **Applied No:** click No → overlay closes
- [ ] **Hide:** click Hide → card dims
- [ ] **Unhide:** click Unhide on hidden card → card restores

## 6. Dashboard (/dashboard)
- [ ] Tabs: Saved / Applied / Hidden / All
- [ ] Saved tab shows saved jobs with count
- [ ] Applied tab shows applied jobs
- [ ] Hidden tab shows hidden jobs
- [ ] All tab shows everything
- [ ] Tab counts match actual job counts
- [ ] Stats bar shows correct numbers
- [ ] Empty state when no jobs tracked

## 7. Analytics (/analytics)
- [ ] Stats cards: Today / This Month / All Time counts
- [ ] Application funnel renders with bars
- [ ] Status pills show breakdown
- [ ] Search bar filters application list
- [ ] Status dropdown on each job → change to "Screening" → updates immediately
- [ ] Change to "Interviewing" → funnel updates
- [ ] Change to "Rejected" → shows in drop-off section
- [ ] Click job title in list → detail modal opens

## 8. Profile (/profile)
- [ ] Display name field → edit → save → refreshes correctly
- [ ] Activity stats (saved/applied/hidden) correct
- [ ] Theme picker: click Light → theme switches, click Dark → back
- [ ] Default filters: set "Remote" as default → Save → go to / → "Remote" filter pre-selected
- [ ] "Apply now" link applies saved filters immediately

## 9. Theme
- [ ] Toggle sun/moon icon in header → theme switches
- [ ] Dark mode: dark backgrounds, light text, proper contrast
- [ ] Light mode: light backgrounds, dark text, proper contrast
- [ ] Theme persists across page navigations
- [ ] Theme persists after browser refresh
- [ ] Login page, about, contact all respect theme

## 10. Static Pages
- [ ] /about → renders with content, ATS list, FAQ
- [ ] /contact → form renders, submit opens mailto
- [ ] Footer visible on all pages
- [ ] Footer links work (Jobs, About, Contact)
- [ ] "Built by Abhinav" links to LinkedIn

## 11. Header / Navigation
- [ ] Logo "Jobsekr" links to home
- [ ] "Jobs" link works
- [ ] "Dashboard" shows saved/applied counts (when logged in)
- [ ] "Analytics" link works (when logged in)
- [ ] Email shown in header (when logged in)
- [ ] Email links to /profile
- [ ] Header is sticky on scroll

## 12. Mobile (test on phone or browser DevTools)
- [ ] Job cards stack single column
- [ ] Filter bar wraps nicely
- [ ] Pagination fits on small screen
- [ ] Modal is scrollable and usable
- [ ] Header nav items accessible
- [ ] All text readable, no overflow

## 13. SEO / Meta
- [ ] Page title: "Jobsekr — Every new tech job, within hours"
- [ ] /job/[id] has dynamic title: "Job Title at Company — Jobsekr"
- [ ] Favicon shows in browser tab
- [ ] OG meta tags present (check with https://metatags.io)

## 14. Performance
- [ ] Home page loads < 2 seconds
- [ ] Search responds < 1 second
- [ ] Dashboard loads < 1 second
- [ ] Modal opens < 500ms
- [ ] No console errors in browser DevTools
- [ ] Lighthouse mobile score > 70