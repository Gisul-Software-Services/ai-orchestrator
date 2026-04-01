"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";
import type { JobRecord } from "@/types/api";

export function useJobPoller(jobId: string | null) {
  const startedAtRef = useRef<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!jobId) {
      startedAtRef.current = null;
      setElapsedSeconds(0);
      return;
    }
    startedAtRef.current = Date.now();
    setElapsedSeconds(0);
    const id = window.setInterval(() => {
      const t0 = startedAtRef.current;
      if (!t0) return;
      setElapsedSeconds(Math.floor((Date.now() - t0) / 1000));
    }, 250);
    return () => window.clearInterval(id);
  }, [jobId]);

  const q = useQuery({
    queryKey: ["admin", "job", jobId],
    enabled: !!jobId,
    queryFn: async () => {
      if (!jobId) throw new Error("jobId is required");
      return adminFetchJson<JobRecord>(`/api/admin/job/${jobId}`);
    },
    refetchInterval: (query) => {
      const data = query.state.data as JobRecord | undefined;
      if (!jobId) return false;
      if (!data) return 2000;
      if (data.status === "complete" || data.status === "failed") return false;
      return 2000;
    },
  });

  const status = q.data?.status ?? (jobId ? "pending" : null);
  const result = q.data?.result ?? null;
  const error =
    q.data?.status === "failed"
      ? (q.data?.error ?? "Job failed")
      : q.error
        ? (q.error as Error).message
        : null;

  return useMemo(
    () => ({
      status,
      result,
      error,
      elapsedSeconds,
      isLoading: q.isLoading,
      isError: q.isError,
      dataUpdatedAt: q.dataUpdatedAt,
    }),
    [status, result, error, elapsedSeconds, q.isLoading, q.isError, q.dataUpdatedAt]
  );
}

