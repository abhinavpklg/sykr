"use client";

import { useEffect, useState } from "react";
import type { Job } from "@/lib/types";
import {
  timeAgo,
  formatSalary,
  atsDisplayName,
  capitalize,
} from "@/lib/utils";
import { useJobActionsContext } from "@/components/JobActionsProvider";

interface JobDetailModalProps {
  job: Job;
  onClose: () => void;
}

export default function JobDetailModal({ job, onClose }: JobDetailModalProps) {
  const { user, getState, saveJob, applyJob, hideJob, unsaveJob, unhideJob } =
    useJobActionsContext();
  const [actionLoading, setActionLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const state = getState(job.id);
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency);
  const isSaved = state?.status === "saved";
  const isApplied = state?.status === "applied";
  const isHidden = state?.status === "hidden";

  const fullDescription = extractDescription(job);
  const plainDescription = fullDescription
    ? fullDescription.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
    : job.description || "";

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(plainDescription);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement("textarea");
      textarea.value = plainDescription;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSave = async () => {
    if (!user) return;
    setActionLoading(true);
    if (isSaved) await unsaveJob(job.id);
    else await saveJob(job.id);
    setActionLoading(false);
  };

  const handleApply = async () => {
    if (!user) return;
    setActionLoading(true);
    await applyJob(job.id);
    setActionLoading(false);
  };

  const handleHide = async () => {
    if (!user) return;
    setActionLoading(true);
    if (isHidden) await unhideJob(job.id);
    else await hideJob(job.id);
    setActionLoading(false);
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto py-8 px-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="relative w-full max-w-2xl rounded-xl border border-border bg-bg-primary shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-md p-1.5 text-t-muted hover:text-t-primary hover:bg-surface transition-colors"
          aria-label="Close"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-6">
          {/* Header */}
          <div className="pr-8">
            <h2 className="text-xl font-bold text-t-primary">{job.title}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-t-secondary">
              {job.company_name && (
                <span className="font-medium text-t-primary">{job.company_name}</span>
              )}
              {job.location && <span>📍 {job.location}</span>}
              <span>🕐 {timeAgo(job.posted_at || job.first_seen)}</span>
            </div>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {job.remote_type !== "unknown" && (
              <Badge
                className={
                  job.remote_type === "remote"
                    ? "bg-red-muted text-red-bright"
                    : job.remote_type === "hybrid"
                    ? "bg-yellow-muted text-yellow-bright"
                    : "bg-accent-muted text-accent"
                }
              >
                {capitalize(job.remote_type)}
              </Badge>
            )}
            <Badge className="bg-surface text-t-muted">{atsDisplayName(job.ats_source)}</Badge>
            {salary && <Badge className="bg-green-muted text-green-bright">{salary}</Badge>}
            {job.seniority && (
              <Badge className="bg-purple-muted text-purple-bright">{capitalize(job.seniority)}</Badge>
            )}
            {job.category && <Badge className="bg-surface text-t-secondary">{job.category}</Badge>}
            {isApplied && <Badge className="bg-green-muted text-green-bright">✓ Applied</Badge>}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-3 mt-5 pb-5 border-b border-border">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md bg-accent px-5 py-2 text-sm font-medium text-t-inverse hover:bg-accent-hover transition-colors"
            >
              Apply on {atsDisplayName(job.ats_source)} →
            </a>

            {user && (
              <>
                <button
                  onClick={handleSave}
                  disabled={actionLoading || isApplied}
                  className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm transition-colors ${
                    isSaved
                      ? "border-accent bg-accent-muted text-accent"
                      : "border-border text-t-secondary hover:border-border-hover hover:text-t-primary"
                  }`}
                >
                  <svg
                    className="h-4 w-4"
                    fill={isSaved ? "currentColor" : "none"}
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                  </svg>
                  {isSaved ? "Saved" : "Save"}
                </button>

                {!isApplied && (
                  <button
                    onClick={handleApply}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm text-t-secondary hover:border-green-bright hover:text-green-bright transition-colors"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Mark Applied
                  </button>
                )}

                <button
                  onClick={handleHide}
                  disabled={actionLoading}
                  className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm transition-colors ${
                    isHidden
                      ? "border-border bg-surface text-t-secondary"
                      : "border-border text-t-muted hover:border-border-hover hover:text-t-secondary"
                  }`}
                >
                  {isHidden ? "Unhide" : "Hide"}
                </button>
              </>
            )}
          </div>

          {/* Description */}
          {(fullDescription || job.description) && (
            <div className="mt-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-t-primary">About this role</h3>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-t-muted hover:text-t-secondary hover:border-border-hover transition-colors"
                >
                  {copied ? (
                    <>
                      <svg className="h-3.5 w-3.5 text-green-bright" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Copied!
                    </>
                  ) : (
                    <>
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy description
                    </>
                  )}
                </button>
              </div>

              {fullDescription ? (
                <div
                  className="prose-custom text-sm text-t-secondary leading-relaxed max-h-[50vh] overflow-y-auto pr-2"
                  dangerouslySetInnerHTML={{ __html: sanitizeHtml(fullDescription) }}
                />
              ) : (
                <p className="text-sm text-t-secondary leading-relaxed whitespace-pre-wrap max-h-[50vh] overflow-y-auto pr-2">
                  {job.description}
                </p>
              )}
            </div>
          )}

          {!fullDescription && !job.description && (
            <div className="mt-5 rounded-lg border border-dashed border-border py-10 text-center">
              <p className="text-sm text-t-muted">Full description available on the original posting.</p>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-sm text-accent hover:underline"
              >
                View on {atsDisplayName(job.ats_source)} →
              </a>
            </div>
          )}

          {/* Details */}
          <div className="mt-5 pt-5 border-t border-border">
            <h3 className="text-sm font-semibold text-t-primary mb-3">Details</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              {job.company_name && <DetailRow label="Company" value={job.company_name} />}
              {job.location && <DetailRow label="Location" value={job.location} />}
              {job.remote_type !== "unknown" && <DetailRow label="Work type" value={capitalize(job.remote_type)} />}
              {salary && <DetailRow label="Salary" value={salary} />}
              {job.seniority && <DetailRow label="Level" value={capitalize(job.seniority)} />}
              {job.category && <DetailRow label="Department" value={job.category} />}
              <DetailRow label="Source" value={atsDisplayName(job.ats_source)} />
              <DetailRow label="First seen" value={new Date(job.first_seen).toLocaleDateString()} />
              {job.posted_at && <DetailRow label="Posted" value={new Date(job.posted_at).toLocaleDateString()} />}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

function Badge({ children, className }: { children: React.ReactNode; className: string }) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-t-muted">{label}</dt>
      <dd className="text-t-primary">{value}</dd>
    </>
  );
}

function extractDescription(job: Job): string | null {
  const raw = job.raw_data;
  if (!raw || typeof raw !== "object") return null;

  if (raw.content && typeof raw.content === "string") return raw.content;
  if (raw.descriptionHtml && typeof raw.descriptionHtml === "string") return raw.descriptionHtml;
  if (raw.description && typeof raw.description === "string") return raw.description;
  if (raw.descriptionPlain && typeof raw.descriptionPlain === "string") return raw.descriptionPlain;

  const attrs = raw.attributes;
  if (attrs && typeof attrs === "object") {
    const a = attrs as Record<string, unknown>;
    if (a.body && typeof a.body === "string") return a.body;
    if (a.description && typeof a.description === "string") return a.description;
  }

  if (raw.requirements && typeof raw.requirements === "string") {
    const desc = (raw.description || "") as string;
    return `${desc}\n\n<h3>Requirements</h3>\n${raw.requirements}`;
  }

  return null;
}

function sanitizeHtml(html: string): string {
  let clean = html.replace(/<(script|style|iframe)[^>]*>[\s\S]*?<\/\1>/gi, "");
  clean = clean.replace(/\s+on\w+="[^"]*"/gi, "");
  clean = clean.replace(/\s+on\w+='[^']*'/gi, "");
  clean = clean.replace(/<a\s/gi, '<a target="_blank" rel="noopener noreferrer" ');
  return clean;
}