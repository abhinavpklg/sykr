"use client";

import { useEffect, useMemo, useState } from "react";
import { createSupabaseBrowser } from "@/lib/supabase-browser";
import { useJobActionsContext } from "@/components/JobActionsProvider";
import type { Job, PipelineStatus } from "@/lib/types";
import { PIPELINE_STATUSES } from "@/lib/types";
import { timeAgo, atsDisplayName } from "@/lib/utils";
import Header from "@/components/Header";
import ApplicationFunnel from "@/components/ApplicationFunnel";
import JobDetailModal from "@/components/JobDetailModal";
import Spinner from "@/components/Spinner";

export default function AnalyticsPage() {
  const { loading: actionsLoading, states, upsertState } = useJobActionsContext();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [search, setSearch] = useState("");
  const [modalJob, setModalJob] = useState<Job | null>(null);
  const supabase = createSupabaseBrowser();

  // Fetch all jobs user has applied to (any pipeline status)
  useEffect(() => {
    const fetchJobs = async () => {
      const pipelineStatuses = PIPELINE_STATUSES.map((s) => s.value);
      const jobIds = Object.entries(states)
        .filter(([, s]) => pipelineStatuses.includes(s.status as PipelineStatus))
        .map(([jobId]) => jobId);

      if (jobIds.length === 0) {
        setJobs([]);
        setLoadingJobs(false);
        return;
      }

      setLoadingJobs(true);
      const { data, error } = await supabase
        .from("jobs")
        .select("*")
        .in("id", jobIds);

      if (error) {
        console.error("Failed to fetch analytics jobs:", error);
      } else {
        setJobs((data as Job[]) || []);
      }
      setLoadingJobs(false);
    };

    if (!actionsLoading) fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [states, actionsLoading]);

  // Compute stats
  const stats = useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    const pipelineStates = Object.values(states).filter((s) =>
      PIPELINE_STATUSES.some((p) => p.value === s.status)
    );

    const todayCount = pipelineStates.filter((s) => {
      const d = new Date(s.applied_at || s.created_at);
      return d >= todayStart;
    }).length;

    const monthCount = pipelineStates.filter((s) => {
      const d = new Date(s.applied_at || s.created_at);
      return d >= monthStart;
    }).length;

    const totalCount = pipelineStates.length;

    // Status breakdown
    const statusCounts: Record<string, number> = {};
    for (const ps of PIPELINE_STATUSES) {
      statusCounts[ps.value] = pipelineStates.filter((s) => s.status === ps.value).length;
    }

    return { todayCount, monthCount, totalCount, statusCounts };
  }, [states]);

  // Filter jobs by search
  const filteredJobs = useMemo(() => {
    const pipelineStatuses = PIPELINE_STATUSES.map((s) => s.value);
    const pipelineJobs = jobs.filter((j) => {
      const s = states[j.id];
      return s && pipelineStatuses.includes(s.status as PipelineStatus);
    });

    if (!search.trim()) return pipelineJobs;

    const q = search.toLowerCase();
    return pipelineJobs.filter(
      (j) =>
        j.title.toLowerCase().includes(q) ||
        (j.company_name || "").toLowerCase().includes(q) ||
        (j.location || "").toLowerCase().includes(q)
    );
  }, [jobs, states, search]);

  // Sort by most recent action
  const sortedJobs = useMemo(() => {
    return [...filteredJobs].sort((a, b) => {
      const sa = states[a.id];
      const sb = states[b.id];
      const da = sa?.applied_at || sa?.updated_at || sa?.created_at || "";
      const db = sb?.applied_at || sb?.updated_at || sb?.created_at || "";
      return db.localeCompare(da);
    });
  }, [filteredJobs, states]);

  const handleStatusChange = async (jobId: string, newStatus: PipelineStatus) => {
    await upsertState(jobId, newStatus);
  };

  const handleOpenModal = async (job: Job) => {
    const { data } = await supabase.from("jobs").select("*").eq("id", job.id).single();
    setModalJob(data ? (data as Job) : job);
  };

  if (actionsLoading) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-5xl px-4 py-10">
          <div className="flex items-center justify-center py-20">
            <Spinner size="lg" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-6">
        <h1 className="text-xl font-bold text-t-primary mb-6">Application Analytics</h1>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <StatCard label="Today" value={stats.todayCount} accent="accent" />
          <StatCard label="This month" value={stats.monthCount} accent="purple-bright" />
          <StatCard label="All time" value={stats.totalCount} accent="green-bright" />
        </div>

        {/* Funnel */}
        {stats.totalCount > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-t-primary mb-4">Application Funnel</h2>
            <ApplicationFunnel statusCounts={stats.statusCounts} total={stats.totalCount} />
          </div>
        )}

        {/* Status breakdown pills */}
        {stats.totalCount > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {PIPELINE_STATUSES.map((ps) => (
              <span
                key={ps.value}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: ps.color }}
                />
                <span className="text-t-secondary">{ps.label}</span>
                <span className="font-medium text-t-primary">{stats.statusCounts[ps.value] || 0}</span>
              </span>
            ))}
          </div>
        )}

        {/* Search */}
        <div className="mb-4">
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search your applications..."
              className="w-full rounded-md border border-border bg-surface py-2 pl-10 pr-4 text-sm text-t-primary placeholder-t-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </div>

        {/* Applications table */}
        {loadingJobs ? (
          <div className="flex items-center justify-center py-20">
            <Spinner />
          </div>
        ) : sortedJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
            <svg className="h-12 w-12 text-t-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-t-primary">
              {search ? "No matching applications" : "No applications yet"}
            </h3>
            <p className="mt-1 text-sm text-t-muted">
              {search
                ? "Try a different search term"
                : "Apply to jobs and track your progress here"}
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
            {/* Table header */}
            <div className="hidden sm:grid grid-cols-[1fr_120px_100px_100px] gap-4 px-4 py-2.5 bg-surface text-xs font-medium text-t-muted border-b border-border">
              <span>Job</span>
              <span>Status</span>
              <span>Applied</span>
              <span>Source</span>
            </div>

            {/* Rows */}
            {sortedJobs.map((job) => {
              const jobState = states[job.id];
              if (!jobState) return null;

              return (
                <div
                  key={job.id}
                  className="grid grid-cols-1 sm:grid-cols-[1fr_120px_100px_100px] gap-2 sm:gap-4 px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-hover transition-colors"
                >
                  {/* Job info */}
                  <div
                    className="cursor-pointer min-w-0"
                    onClick={() => handleOpenModal(job)}
                  >
                    <p className="text-sm font-medium text-t-primary truncate hover:text-accent transition-colors">
                      {job.title}
                    </p>
                    <p className="text-xs text-t-muted truncate">
                      {job.company_name}
                      {job.location && ` · ${job.location}`}
                    </p>
                  </div>

                  {/* Status dropdown */}
                  <div className="flex items-center">
                    <select
                      value={jobState.status}
                      onChange={(e) => handleStatusChange(job.id, e.target.value as PipelineStatus)}
                      className="w-full rounded border border-border bg-surface px-2 py-1 text-xs text-t-secondary focus:border-accent focus:outline-none"
                      style={{
                        borderLeftColor:
                          PIPELINE_STATUSES.find((p) => p.value === jobState.status)?.color || "var(--border)",
                        borderLeftWidth: "3px",
                      }}
                    >
                      {PIPELINE_STATUSES.map((ps) => (
                        <option key={ps.value} value={ps.value}>
                          {ps.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Applied date */}
                  <div className="flex items-center text-xs text-t-muted">
                    {timeAgo(jobState.applied_at || jobState.created_at)}
                  </div>

                  {/* Source */}
                  <div className="flex items-center text-xs text-t-muted">
                    {atsDisplayName(job.ats_source)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {modalJob && <JobDetailModal job={modalJob} onClose={() => setModalJob(null)} />}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5 text-center">
      <p className={`text-3xl font-bold text-${accent}`}>{value}</p>
      <p className="text-xs text-t-muted mt-1">{label}</p>
    </div>
  );
}