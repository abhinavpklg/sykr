"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useJobActionsContext } from "@/components/JobActionsProvider";
import { useTheme } from "@/components/ThemeProvider";
import { createSupabaseBrowser } from "@/lib/supabase-browser";
import Spinner from "@/components/Spinner";

export default function Header() {
  const { user, loading, counts } = useJobActionsContext();
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const supabase = createSupabaseBrowser();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg-primary/95 backdrop-blur supports-[backdrop-filter]:bg-bg-primary/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight text-t-primary hover:text-accent transition-colors"
          >
            Jobsekr
          </Link>
          <nav className="hidden sm:flex items-center gap-4">
            <Link
              href="/"
              className="text-sm text-t-secondary hover:text-t-primary transition-colors"
            >
              Jobs
            </Link>
            {user && (
              <Link
                href="/dashboard"
                className="flex items-center gap-2 text-sm text-t-secondary hover:text-t-primary transition-colors"
              >
                Dashboard
                {counts.total > 0 && (
                  <span className="flex items-center gap-1.5 text-xs">
                    <span className="rounded-full bg-accent-muted px-1.5 py-0.5 text-accent">
                      {counts.saved}
                    </span>
                    <span className="rounded-full bg-green-muted px-1.5 py-0.5 text-green-bright">
                      {counts.applied}
                    </span>
                  </span>
                )}
              </Link>
            )}
            {user && (
              <Link
                href="/analytics"
                className="text-sm text-t-secondary hover:text-t-primary transition-colors"
              >
                Analytics
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-md p-2 text-t-muted hover:text-t-primary hover:bg-surface transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>

          {loading ? (
            <Spinner size="sm" />
          ) : user ? (
            <div className="flex items-center gap-3">
              <Link
                href="/profile"
                className="hidden sm:inline text-sm text-t-secondary hover:text-t-primary transition-colors"
              >
                {user.email}
              </Link>
              <button
                onClick={handleSignOut}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-t-secondary hover:border-border-hover hover:text-t-primary transition-colors"
              >
                Sign out
              </button>
            </div>
          ) : (
            <Link
              href="/auth/login"
              className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-t-inverse hover:bg-accent-hover transition-colors"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}