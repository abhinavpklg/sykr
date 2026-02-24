"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useJobActionsContext } from "@/components/JobActionsProvider";
import { createSupabaseBrowser } from "@/lib/supabase-browser";

export default function Header() {
  const { user, loading, counts } = useJobActionsContext();
  const router = useRouter();
  const supabase = createSupabaseBrowser();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-50 border-b border-gray-800 bg-[#0d1117]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0d1117]/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight text-white hover:text-accent transition-colors"
          >
            Jobsekr
          </Link>
          <nav className="hidden sm:flex items-center gap-4">
            <Link
              href="/"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Jobs
            </Link>
            {user && (
              <Link
                href="/dashboard"
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Dashboard
                {counts.total > 0 && (
                  <span className="flex items-center gap-1.5 text-xs">
                    <span className="rounded-full bg-accent/20 px-1.5 py-0.5 text-accent">
                      {counts.saved}
                    </span>
                    <span className="rounded-full bg-green-bright/20 px-1.5 py-0.5 text-green-bright">
                      {counts.applied}
                    </span>
                  </span>
                )}
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {loading ? (
            <div className="h-8 w-20 animate-pulse rounded bg-surface" />
          ) : user ? (
            <div className="flex items-center gap-3">
              <span className="hidden sm:inline text-sm text-gray-400">
                {user.email}
              </span>
              <button
                onClick={handleSignOut}
                className="rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
              >
                Sign out
              </button>
            </div>
          ) : (
            <Link
              href="/auth/login"
              className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent/90 transition-colors"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}