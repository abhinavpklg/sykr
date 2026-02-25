"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState, useTransition } from "react";
import { REMOTE_OPTIONS, ATS_OPTIONS, SORT_OPTIONS, LOCATION_OPTIONS } from "@/lib/types";

interface FilterBarProps {
  totalJobs: number;
}

export default function FilterBar({ totalJobs }: FilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [query, setQuery] = useState(searchParams.get("q") || "");

  const updateFilters = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page");

      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
    },
    [router, searchParams]
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters("q", query);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setQuery("");
      updateFilters("q", "");
      (e.target as HTMLInputElement).blur();
    }
  };

  // Global keyboard shortcut: "/" to focus search
  const searchRef = useCallback((node: HTMLInputElement | null) => {
    if (!node) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA" && document.activeElement?.tagName !== "SELECT") {
        e.preventDefault();
        node.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const selectClass =
    "rounded-md border border-border bg-surface px-3 py-2 text-sm text-t-secondary focus:border-accent focus:outline-none";

  return (
    <div className="sticky top-14 z-40 border-b border-border bg-bg-primary/95 backdrop-blur supports-[backdrop-filter]:bg-bg-primary/80">
      <div className="mx-auto max-w-7xl px-4 py-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                ref={searchRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search jobs... (press / to focus)"
                className="w-full rounded-md border border-border bg-surface py-2 pl-10 pr-4 text-sm text-t-primary placeholder-t-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </form>

          {/* Filters row */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={searchParams.get("remote") || ""}
              onChange={(e) => updateFilters("remote", e.target.value)}
              className={selectClass}
            >
              {REMOTE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              value={searchParams.get("ats") || ""}
              onChange={(e) => updateFilters("ats", e.target.value)}
              className={selectClass}
            >
              {ATS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              value={searchParams.get("location") || ""}
              onChange={(e) => updateFilters("location", e.target.value)}
              className={selectClass}
            >
              {LOCATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              value={searchParams.get("sort") || "recent"}
              onChange={(e) => updateFilters("sort", e.target.value)}
              className={selectClass}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <span className="ml-auto text-xs text-t-muted whitespace-nowrap">
              {isPending ? "Loading..." : <>{totalJobs.toLocaleString()} jobs</>}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}