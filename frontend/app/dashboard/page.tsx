"use client";

import { useEffect, useState } from "react";
import { createSupabaseBrowser } from "@/lib/supabase-browser";
import { useJobActionsContext } from "@/components/JobActionsProvider";
import type { Job } from "@/lib/types";
import Header from "@/components/Header";
import JobCard from "@/components/JobCard";

type Tab = "saved" | "applied" | "hidden" | "all";

const TABS: { key: Tab; label: string }[] = [
  { key: "saved", label: "Saved" },
  { key: "applied", label: "Applied" },
  { key: "hidden", label: "Hidden" },
  { key: "all", label: "All" },
];

export default function DashboardPage() {
  const { loading: actionsLoading, states, counts } =
    useJobActionsContext();
  const [activeTab, setActiveTab] = useState<Tab>("saved");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  const supabase = createSupabaseBrowser();

  // Fetch all jobs that the user has interacted with
  useEffect(() => {
    const fetchJobs = async () => {
      const jobIds = Object.keys(states);
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
        console.error("Failed to fetch dashboard jobs:", error);
      } else {
        setJobs((data as Job[]) || []);
      }

      setLoadingJobs(false);
    };

    if (!actionsLoading) {
      fetchJobs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [states, actionsLoading]);

  // Filter jobs by active tab
  const filteredJobs = jobs.filter((job) => {
    const state = states[job.id];
    if (!state) return false;
    if (activeTab === "all") return true;
    return state.status === activeTab;
  });

  // Sort: most recent action first
  filteredJobs.sort((a, b) => {
    const stateA = states[a.id];
    const stateB = states[b.id];
    const dateA = stateA?.updated_at || stateA?.created_at || "";
    const dateB = stateB?.updated_at || stateB?.created_at || "";
    return dateB.localeCompare(dateA);
  });

  const tabCount = (tab: Tab): number => {
    if (tab === "all") return counts.total;
    return counts[tab];
  };

  if (actionsLoading) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-7xl px-4 py-10">
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-accent" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Stats bar */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <h1 className="text-xl font-bold text-white">My Applications</h1>
          <div className="flex items-center gap-3 ml-auto">
            <div className="flex items-center gap-1.5 text-sm">
              <span className="inline-block h-2 w-2 rounded-full bg-accent" />
              <span className="text-gray-400">
                {counts.saved} saved
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-sm">
              <span className="inline-block h-2 w-2 rounded-full bg-green-bright" />
              <span className="text-gray-400">
                {counts.applied} applied
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-sm">
              <span className="inline-block h-2 w-2 rounded-full bg-gray-600" />
              <span className="text-gray-400">
                {counts.hidden} hidden
              </span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-800 mb-6">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
                activeTab === tab.key
                  ? "text-white"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {tab.label}
              <span
                className={`ml-1.5 text-xs ${
                  activeTab === tab.key ? "text-accent" : "text-gray-600"
                }`}
              >
                {tabCount(tab.key)}
              </span>
              {activeTab === tab.key && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </button>
          ))}
        </div>

        {/* Job list */}
        {loadingJobs ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-accent" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-700 py-20 text-center">
            <svg
              className="h-12 w-12 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-300">
              {activeTab === "all"
                ? "No tracked jobs yet"
                : `No ${activeTab} jobs`}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {activeTab === "all"
                ? "Browse jobs and save, apply, or hide them to track here."
                : `Jobs you mark as "${activeTab}" will appear here.`}
            </p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}