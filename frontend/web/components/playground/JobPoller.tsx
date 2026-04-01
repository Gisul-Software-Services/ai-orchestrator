"use client";

import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useJobPoller } from "@/hooks/useJobPoller";
import type { JobRecord } from "@/types/api";

export function JobPoller({
  jobId,
  onComplete,
  onError,
}: {
  jobId: string | null;
  onComplete: (result: unknown) => void;
  onError: (message: string) => void;
}) {
  const poll = useJobPoller(jobId);

  useEffect(() => {
    if (!jobId) return;
    if (poll.status === "complete") {
      onComplete(poll.result);
    } else if (poll.status === "failed") {
      onError(poll.error || "Job failed");
    }
  }, [jobId, poll.status, poll.result, poll.error, onComplete, onError]);

  if (!jobId) return null;

  if (poll.status === "pending" || poll.status === "processing") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-200">
        <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />
        <span>
          Generating… <span className="text-zinc-400">({poll.elapsedSeconds}s)</span>
        </span>
      </div>
    );
  }

  return null;
}

