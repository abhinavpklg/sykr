"use client";

import { useCallback, useEffect, useState } from "react";
import { createSupabaseBrowser } from "@/lib/supabase-browser";
import type { UserJobState } from "@/lib/types";
import type { User } from "@supabase/supabase-js";

interface JobStates {
  [jobId: string]: UserJobState;
}

export function useJobActions() {
  const [user, setUser] = useState<User | null>(null);
  const [states, setStates] = useState<JobStates>({});
  const [loading, setLoading] = useState(true);
  const supabase = createSupabaseBrowser();

  // Load user + all their job states
  useEffect(() => {
    const init = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      setUser(user);

      if (user) {
        const { data } = await supabase
          .from("user_job_state")
          .select("*")
          .eq("user_id", user.id);

        if (data) {
          const map: JobStates = {};
          for (const s of data as UserJobState[]) {
            map[s.job_id] = s;
          }
          setStates(map);
        }
      }
      setLoading(false);
    };

    init();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (!session?.user) {
        setStates({});
      }
    });

    return () => subscription.unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const upsertState = useCallback(
    async (
      jobId: string,
      status: UserJobState["status"],
      extra?: Partial<Pick<UserJobState, "notes" | "applied_at">>
    ): Promise<boolean> => {
      if (!user) return false;

      const row: Record<string, unknown> = {
        user_id: user.id,
        job_id: jobId,
        status,
        updated_at: new Date().toISOString(),
      };

      if (status === "applied") {
        row.applied_at = extra?.applied_at || new Date().toISOString();
      }

      if (extra?.notes !== undefined) {
        row.notes = extra.notes;
      }

      const { data, error } = await supabase
        .from("user_job_state")
        .upsert(row, { onConflict: "user_id,job_id" })
        .select()
        .single();

      if (error) {
        console.error("Failed to upsert job state:", error);
        return false;
      }

      if (data) {
        setStates((prev) => ({
          ...prev,
          [jobId]: data as UserJobState,
        }));
      }

      return true;
    },
    [user, supabase]
  );

  const removeState = useCallback(
    async (jobId: string): Promise<boolean> => {
      if (!user) return false;

      const { error } = await supabase
        .from("user_job_state")
        .delete()
        .eq("user_id", user.id)
        .eq("job_id", jobId);

      if (error) {
        console.error("Failed to remove job state:", error);
        return false;
      }

      setStates((prev) => {
        const next = { ...prev };
        delete next[jobId];
        return next;
      });

      return true;
    },
    [user, supabase]
  );

  const saveJob = useCallback(
    (jobId: string) => upsertState(jobId, "saved"),
    [upsertState]
  );

  const applyJob = useCallback(
    (jobId: string) => upsertState(jobId, "applied"),
    [upsertState]
  );

  const hideJob = useCallback(
    (jobId: string) => upsertState(jobId, "hidden"),
    [upsertState]
  );

  const unhideJob = useCallback(
    (jobId: string) => removeState(jobId),
    [removeState]
  );

  const unsaveJob = useCallback(
    (jobId: string) => removeState(jobId),
    [removeState]
  );

  const getState = useCallback(
    (jobId: string): UserJobState | null => states[jobId] || null,
    [states]
  );

  const counts = {
    saved: Object.values(states).filter((s) => s.status === "saved").length,
    applied: Object.values(states).filter((s) => s.status === "applied").length,
    hidden: Object.values(states).filter((s) => s.status === "hidden").length,
    total: Object.keys(states).length,
  };

  return {
    user,
    loading,
    states,
    counts,
    getState,
    saveJob,
    applyJob,
    hideJob,
    unhideJob,
    unsaveJob,
    upsertState,
    removeState,
  };
}