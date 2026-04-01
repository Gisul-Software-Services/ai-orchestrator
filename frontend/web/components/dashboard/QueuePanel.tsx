"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";

export function QueuePanel({
  loading,
  error,
  lastOkAt,
  queues,
}: {
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  queues:
    | {
        active_jobs: number;
        jobs_in_store: number;
        queue_depths: Record<string, number>;
      }
    | null;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-50">Queue status</div>
          <div className="text-xs text-zinc-400">
            Batch queues + job store snapshot
          </div>
        </div>
        <LiveIndicator ok={!error} label={!error ? "Live" : "Degraded"} />
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-4 w-56" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          <div className="font-medium">Could not reach model-service</div>
          <div className="mt-1 text-xs text-amber-200/80">
            Last successful fetch:{" "}
            {lastOkAt ? new Date(lastOkAt).toLocaleString() : "never"}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm text-zinc-200">
            <span>Active jobs</span>
            <span className="font-medium text-zinc-50">
              {queues?.active_jobs ?? 0}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm text-zinc-200">
            <span>Jobs in store</span>
            <span className="font-medium text-zinc-50">
              {queues?.jobs_in_store ?? 0}
            </span>
          </div>
          <div className="pt-2">
            <div className="mb-2 text-xs font-medium text-zinc-400">
              Queue depths
            </div>
            <div className="space-y-1">
              {Object.entries(queues?.queue_depths ?? {})
                .sort((a, b) => b[1] - a[1])
                .map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between rounded-md bg-zinc-900/40 px-2 py-1 text-sm"
                  >
                    <span className="text-zinc-200">{k}</span>
                    <span className="font-medium text-zinc-50">{v}</span>
                  </div>
                ))}
              {Object.keys(queues?.queue_depths ?? {}).length === 0 ? (
                <div className="text-xs text-zinc-500">No queue data.</div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

