-- ============================================================================
-- SYKR — Initial Schema Migration  
-- Run this in Supabase SQL Editor (or via supabase db push)
-- ============================================================================


-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. COMPANIES
-- ============================================================================
CREATE TABLE companies (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    slug            TEXT NOT NULL,
    ats             TEXT NOT NULL,
    name            TEXT,
    api_url         TEXT,
    careers_url     TEXT,
    logo_url        TEXT,
    verified        BOOLEAN DEFAULT false,
    job_count       INTEGER DEFAULT 0,
    last_scraped_at TIMESTAMPTZ,
    sources         TEXT[] DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(ats, slug)
);

CREATE INDEX idx_companies_ats ON companies(ats);
CREATE INDEX idx_companies_verified ON companies(verified);
CREATE INDEX idx_companies_slug ON companies(slug);
CREATE INDEX idx_companies_last_scraped ON companies(last_scraped_at);

-- ============================================================================
-- 2. JOBS
-- ============================================================================
CREATE TABLE jobs (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    url_hash        TEXT NOT NULL UNIQUE,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    company_name    TEXT,
    company_id      UUID REFERENCES companies(id) ON DELETE SET NULL,
    location        TEXT,
    description     TEXT,
    salary_min      INTEGER,
    salary_max      INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    remote_type     TEXT CHECK (remote_type IN ('remote', 'onsite', 'hybrid', 'unknown')) DEFAULT 'unknown',
    seniority       TEXT,
    ats_source      TEXT NOT NULL,
    platform        TEXT,
    category        TEXT,
    tags            TEXT[] DEFAULT '{}',
    easy_apply      BOOLEAN DEFAULT false,
    posted_at       TIMESTAMPTZ,
    first_seen      TIMESTAMPTZ DEFAULT now(),
    last_seen       TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT true,
    raw_data        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_jobs_url_hash ON jobs(url_hash);
CREATE INDEX idx_jobs_title_search ON jobs USING gin(to_tsvector('english', title));
CREATE INDEX idx_jobs_company ON jobs(company_name);
CREATE INDEX idx_jobs_company_id ON jobs(company_id);
CREATE INDEX idx_jobs_ats ON jobs(ats_source);
CREATE INDEX idx_jobs_remote ON jobs(remote_type);
CREATE INDEX idx_jobs_first_seen ON jobs(first_seen DESC);
CREATE INDEX idx_jobs_posted_at ON jobs(posted_at DESC);
CREATE INDEX idx_jobs_active ON jobs(is_active);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_active_first_seen ON jobs(is_active, first_seen DESC);
CREATE INDEX idx_jobs_salary ON jobs(salary_min, salary_max) WHERE salary_min IS NOT NULL;

-- ============================================================================
-- 3. USER JOB STATE (application tracking)
-- ============================================================================
CREATE TABLE user_job_state (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status      TEXT NOT NULL CHECK (status IN ('saved', 'applied', 'hidden', 'interviewed', 'rejected', 'offered')),
    notes       TEXT,
    applied_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX idx_ujs_user ON user_job_state(user_id);
CREATE INDEX idx_ujs_status ON user_job_state(user_id, status);
CREATE INDEX idx_ujs_job ON user_job_state(job_id);

-- ============================================================================
-- 4. USER PROFILES (extends auth.users)
-- ============================================================================
CREATE TABLE user_profiles (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    email       TEXT,
    avatar_url  TEXT,
    preferences JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_profiles_user ON user_profiles(user_id);

-- ============================================================================
-- 5. SAVED FILTERS (user search presets)
-- ============================================================================
CREATE TABLE saved_filters (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    filters     JSONB NOT NULL DEFAULT '{}',
    is_default  BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_saved_filters_user ON saved_filters(user_id);

-- ============================================================================
-- 6. SCRAPE RUNS (pipeline monitoring)
-- ============================================================================
CREATE TABLE scrape_runs (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source      TEXT NOT NULL,
    job_title   TEXT,
    config      JSONB DEFAULT '{}',
    total_found INTEGER DEFAULT 0,
    new_found   INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    started_at  TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status      TEXT DEFAULT 'running'
);

CREATE INDEX idx_scrape_runs_source ON scrape_runs(source);
CREATE INDEX idx_scrape_runs_started ON scrape_runs(started_at DESC);
CREATE INDEX idx_scrape_runs_status ON scrape_runs(status);

-- ============================================================================
-- 7. ROW LEVEL SECURITY
-- ============================================================================

-- Jobs: anyone can read, only service role can write
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Jobs are publicly readable"
    ON jobs FOR SELECT
    USING (true);
CREATE POLICY "Service role can insert jobs"
    ON jobs FOR INSERT
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Service role can update jobs"
    ON jobs FOR UPDATE
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Service role can delete jobs"
    ON jobs FOR DELETE
    USING (auth.role() = 'service_role');

-- Companies: public read, service write
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Companies are publicly readable"
    ON companies FOR SELECT
    USING (true);
CREATE POLICY "Service role can insert companies"
    ON companies FOR INSERT
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Service role can update companies"
    ON companies FOR UPDATE
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Service role can delete companies"
    ON companies FOR DELETE
    USING (auth.role() = 'service_role');

-- User job state: users can only access their own data
ALTER TABLE user_job_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own job state"
    ON user_job_state FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own job state"
    ON user_job_state FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own job state"
    ON user_job_state FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own job state"
    ON user_job_state FOR DELETE
    USING (auth.uid() = user_id);

-- User profiles: users can read/write only their own profile
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Saved filters: users can only access their own filters
ALTER TABLE saved_filters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own filters"
    ON saved_filters FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own filters"
    ON saved_filters FOR INSERT
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own filters"
    ON saved_filters FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own filters"
    ON saved_filters FOR DELETE
    USING (auth.uid() = user_id);

-- Scrape runs: public read, service write
ALTER TABLE scrape_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Scrape runs are publicly readable"
    ON scrape_runs FOR SELECT
    USING (true);
CREATE POLICY "Service role can insert scrape runs"
    ON scrape_runs FOR INSERT
    WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Service role can update scrape runs"
    ON scrape_runs FOR UPDATE
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- 8. AUTO-CREATE PROFILE ON SIGNUP (trigger)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, email, display_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        ),
        COALESCE(
            NEW.raw_user_meta_data->>'avatar_url',
            NEW.raw_user_meta_data->>'picture'
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop if exists to make migration idempotent
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- 9. HELPER FUNCTIONS
-- ============================================================================

-- Updated_at auto-update trigger for tables that need it
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER user_job_state_updated_at
    BEFORE UPDATE ON user_job_state
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER saved_filters_updated_at
    BEFORE UPDATE ON saved_filters
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();