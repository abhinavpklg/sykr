// ============================================================================
// SYKR — TypeScript types matching Supabase schema
// ============================================================================

export interface Company {
  id: string;
  slug: string;
  ats: string;
  name: string | null;
  api_url: string | null;
  careers_url: string | null;
  logo_url: string | null;
  verified: boolean;
  job_count: number;
  last_scraped_at: string | null;
  sources: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  url_hash: string;
  url: string;
  title: string;
  company_name: string | null;
  company_id: string | null;
  location: string | null;
  description: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  remote_type: "remote" | "onsite" | "hybrid" | "unknown";
  seniority: string | null;
  ats_source: string;
  platform: string | null;
  category: string | null;
  tags: string[];
  easy_apply: boolean;
  posted_at: string | null;
  first_seen: string;
  last_seen: string;
  expires_at: string | null;
  is_active: boolean;
  raw_data: Record<string, unknown>;
  created_at: string;
}

export interface UserJobState {
  id: string;
  user_id: string;
  job_id: string;
  status: "saved" | "applied" | "screening" | "interviewing" | "offered" | "rejected" | "archived" | "hidden";
  notes: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  display_name: string | null;
  email: string | null;
  avatar_url: string | null;
  preferences: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SavedFilter {
  id: string;
  user_id: string;
  name: string;
  filters: FilterParams;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScrapeRun {
  id: string;
  source: string;
  job_title: string | null;
  config: Record<string, unknown>;
  total_found: number;
  new_found: number;
  errors: number;
  started_at: string;
  finished_at: string | null;
  status: string;
}

// ============================================================================
// Filter / Query types
// ============================================================================

export interface FilterParams {
  query?: string;
  remote_type?: string;
  ats_source?: string;
  location?: string;
  salary_min?: number;
  sort?: "recent" | "oldest";
}

export interface JobWithState extends Job {
  user_state?: UserJobState | null;
}

// ============================================================================
// Helpers
// ============================================================================

export const REMOTE_OPTIONS = [
  { value: "", label: "All" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
] as const;

export const ATS_OPTIONS = [
  { value: "", label: "All Sources" },
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
  { value: "ashby", label: "Ashby" },
  { value: "workable", label: "Workable" },
  { value: "smartrecruiters", label: "SmartRecruiters" },
  { value: "recruitee", label: "Recruitee" },
  { value: "dover", label: "Dover" },
  { value: "breezy", label: "Breezy" },
  { value: "bamboohr", label: "BambooHR" },
  { value: "teamtailor", label: "Teamtailor" },
  { value: "pinpoint", label: "Pinpoint" },
  { value: "rippling", label: "Rippling" },
  { value: "personio", label: "Personio" },
  { value: "freshteam", label: "Freshteam" },
] as const;

export const LOCATION_OPTIONS = [
  { value: "", label: "All Locations" },
  { value: "United States", label: "United States" },
  { value: "Remote", label: "Remote" },
  { value: "San Francisco", label: "San Francisco" },
  { value: "New York", label: "New York" },
  { value: "Seattle", label: "Seattle" },
  { value: "Austin", label: "Austin" },
  { value: "Los Angeles", label: "Los Angeles" },
  { value: "Chicago", label: "Chicago" },
  { value: "Boston", label: "Boston" },
  { value: "Denver", label: "Denver" },
  { value: "London", label: "London" },
  { value: "Berlin", label: "Berlin" },
  { value: "Toronto", label: "Toronto" },
  { value: "India", label: "India" },
  { value: "Europe", label: "Europe" },
] as const;

export const SORT_OPTIONS = [
  { value: "recent", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
] as const;

export const TIME_RANGE_OPTIONS = [
  { value: "", label: "All time" },
  { value: "1", label: "Past 24 hours" },
  { value: "3", label: "3 days" },
  { value: "7", label: "1 week" },
  { value: "14", label: "2 weeks" },
  { value: "21", label: "3 weeks" },
  { value: "30", label: "1 month" },
  { value: "60", label: "2 months" },
  { value: "90", label: "3 months" },
] as const;

// Application pipeline statuses (order matters for funnel)
export const PIPELINE_STATUSES = [
  { value: "applied", label: "Applied", color: "var(--accent)" },
  { value: "screening", label: "Screening", color: "var(--yellow)" },
  { value: "interviewing", label: "Interviewing", color: "var(--purple)" },
  { value: "offered", label: "Offered", color: "var(--green)" },
  { value: "rejected", label: "Rejected", color: "var(--red)" },
  { value: "archived", label: "Archived", color: "var(--text-muted)" },
] as const;

export type PipelineStatus = typeof PIPELINE_STATUSES[number]["value"];