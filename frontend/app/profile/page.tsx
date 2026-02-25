"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createSupabaseBrowser } from "@/lib/supabase-browser";
import { useJobActionsContext } from "@/components/JobActionsProvider";
import { useTheme } from "@/components/ThemeProvider";
import { REMOTE_OPTIONS, ATS_OPTIONS, LOCATION_OPTIONS, SORT_OPTIONS } from "@/lib/types";
import type { UserProfile } from "@/lib/types";
import Header from "@/components/Header";
import Spinner from "@/components/Spinner";

interface Preferences {
  default_query?: string;
  default_remote?: string;
  default_ats?: string;
  default_location?: string;
  default_sort?: string;
  theme?: "dark" | "light";
}

export default function ProfilePage() {
  const { user, loading: actionsLoading, counts } = useJobActionsContext();
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const supabase = createSupabaseBrowser();

  const [, setProfile] = useState<UserProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [prefs, setPrefs] = useState<Preferences>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!user) return;

      const { data, error } = await supabase
        .from("user_profiles")
        .select("*")
        .eq("user_id", user.id)
        .single();

      if (error) {
        console.error("Failed to fetch profile:", error);
      } else if (data) {
        const p = data as UserProfile;
        setProfile(p);
        setDisplayName(p.display_name || "");
        setPrefs((p.preferences as Preferences) || {});
      }

      setLoading(false);
    };

    if (!actionsLoading) fetchProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, actionsLoading]);

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    setMessage(null);

    const updatedPrefs: Preferences = { ...prefs, theme };

    const { error } = await supabase
      .from("user_profiles")
      .update({
        display_name: displayName.trim() || null,
        preferences: updatedPrefs,
      })
      .eq("user_id", user.id);

    if (error) {
      setMessage("Failed to save. Please try again.");
      console.error("Profile save error:", error);
    } else {
      setMessage("Profile saved!");
      setPrefs(updatedPrefs);
      setTimeout(() => setMessage(null), 3000);
    }

    setSaving(false);
  };

  const handleApplyDefaults = () => {
    const params = new URLSearchParams();
    if (prefs.default_query) params.set("q", prefs.default_query);
    if (prefs.default_remote) params.set("remote", prefs.default_remote);
    if (prefs.default_ats) params.set("ats", prefs.default_ats);
    if (prefs.default_location) params.set("location", prefs.default_location);
    if (prefs.default_sort) params.set("sort", prefs.default_sort);

    router.push(`/?${params.toString()}`);
  };

  const updatePref = (key: keyof Preferences, value: string) => {
    setPrefs((prev) => ({ ...prev, [key]: value || undefined }));
  };

  const selectClass =
    "w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-t-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent";

  if (actionsLoading || loading) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-2xl px-4 py-10">
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
      <main className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-xl font-bold text-t-primary mb-8">Profile & Preferences</h1>

        {/* Profile section */}
        <section className="rounded-lg border border-border bg-surface p-6 mb-6">
          <h2 className="text-sm font-semibold text-t-primary mb-4">Account</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-t-secondary mb-1">Email</label>
              <p className="text-sm text-t-muted">{user?.email}</p>
            </div>

            <div>
              <label htmlFor="displayName" className="block text-sm text-t-secondary mb-1">
                Display name
              </label>
              <input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className={selectClass}
                placeholder="Your name"
              />
            </div>
          </div>
        </section>

        {/* Stats section */}
        <section className="rounded-lg border border-border bg-surface p-6 mb-6">
          <h2 className="text-sm font-semibold text-t-primary mb-4">Your Activity</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-accent">{counts.saved}</p>
              <p className="text-xs text-t-muted mt-1">Saved</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-bright">{counts.applied}</p>
              <p className="text-xs text-t-muted mt-1">Applied</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-t-muted">{counts.hidden}</p>
              <p className="text-xs text-t-muted mt-1">Hidden</p>
            </div>
          </div>
        </section>

        {/* Appearance */}
        <section className="rounded-lg border border-border bg-surface p-6 mb-6">
          <h2 className="text-sm font-semibold text-t-primary mb-4">Appearance</h2>
          <div>
            <label className="block text-sm text-t-secondary mb-1">Theme</label>
            <div className="flex gap-2">
              <button
                onClick={() => setTheme("dark")}
                className={`flex-1 rounded-md border px-4 py-2 text-sm transition-colors ${
                  theme === "dark"
                    ? "border-accent bg-accent-muted text-accent"
                    : "border-border text-t-secondary hover:border-border-hover"
                }`}
              >
                🌙 Dark
              </button>
              <button
                onClick={() => setTheme("light")}
                className={`flex-1 rounded-md border px-4 py-2 text-sm transition-colors ${
                  theme === "light"
                    ? "border-accent bg-accent-muted text-accent"
                    : "border-border text-t-secondary hover:border-border-hover"
                }`}
              >
                ☀️ Light
              </button>
            </div>
          </div>
        </section>

        {/* Default filters */}
        <section className="rounded-lg border border-border bg-surface p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-t-primary">Default Filters</h2>
            <button
              onClick={handleApplyDefaults}
              className="text-xs text-accent hover:underline"
            >
              Apply now →
            </button>
          </div>
          <p className="text-xs text-t-muted mb-4">
            These filters will be applied automatically when you visit the jobs page.
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-t-secondary mb-1">Default search query</label>
              <input
                type="text"
                value={prefs.default_query || ""}
                onChange={(e) => updatePref("default_query", e.target.value)}
                className={selectClass}
                placeholder="e.g. react, python, full stack"
              />
            </div>

            <div>
              <label className="block text-sm text-t-secondary mb-1">Work type</label>
              <select
                value={prefs.default_remote || ""}
                onChange={(e) => updatePref("default_remote", e.target.value)}
                className={selectClass}
              >
                {REMOTE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-t-secondary mb-1">ATS source</label>
              <select
                value={prefs.default_ats || ""}
                onChange={(e) => updatePref("default_ats", e.target.value)}
                className={selectClass}
              >
                {ATS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-t-secondary mb-1">Location</label>
              <select
                value={prefs.default_location || ""}
                onChange={(e) => updatePref("default_location", e.target.value)}
                className={selectClass}
              >
                {LOCATION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-t-secondary mb-1">Sort order</label>
              <select
                value={prefs.default_sort || "recent"}
                onChange={(e) => updatePref("default_sort", e.target.value)}
                className={selectClass}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* Save button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-accent px-6 py-2.5 text-sm font-medium text-t-inverse hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save preferences"}
          </button>
          {message && (
            <span className={`text-sm ${message.includes("Failed") ? "text-red-bright" : "text-green-bright"}`}>
              {message}
            </span>
          )}
        </div>
      </main>
    </div>
  );
}