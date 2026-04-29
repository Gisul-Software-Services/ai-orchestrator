"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";
import { cn } from "@/lib/utils";

function depthColor(v: number): string {
  if (v === 0) return "bg-zinc-700";
  if (v <= 5) return "bg-console-emerald";
  if (v <= 20) return "bg-console-amber";
  return "bg-console-red";
}

function depthTextColor(v: number): string {
  if (v === 0) return "text-zinc-500";
  if (v <= 5) return "text-emerald-400";
  if (v <= 20) return "text-amber-400";
  return "text-red-400";
}

export function QueuePanel({
  loading,
  error,
  lastOkAt,
  queues,
}: {
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  queues: {
    active_jobs: number;
    jobs_in_store: number;
    queue_depths: Record<string, number>;
  } | null;
}) {
  const sortedQueues = Object.entries(queues?.queue_depths ?? {}).sort(
    (a, b) => b[1] - a[1]
  );
  const isEmpty = sortedQueues.length === 0;
  const maxDepth = Math.max(1, ...sortedQueues.map(([, v]) => v));

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-100">Queue status</div>
          <div className="text-xs text-zinc-500">Batch queues + job store</div>
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
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">
          <div className="font-medium">Service unreachable</div>
          <div className="mt-1 text-xs text-amber-300/70">
            Last fetch: {lastOkAt ? new Date(lastOkAt).toLocaleString() : "never"}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Summary row */}
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2">
              <div className="text-[10px] uppercase tracking-wide text-zinc-600">Active jobs</div>
              <div className="mt-0.5 text-lg font-bold text-zinc-100">
                {queues?.active_jobs ?? 0}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2">
              <div className="text-[10px] uppercase tracking-wide text-zinc-600">In store</div>
              <div className="mt-0.5 text-lg font-bold text-zinc-100">
                {queues?.jobs_in_store ?? 0}
              </div>
            </div>
          </div>

          {/* Queue depths */}
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
              Queue depths
            </div>
            {isEmpty ? (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5">
                <span className="dot-emerald" />
                <div>
                  <div className="text-sm font-medium text-emerald-400">All queues empty</div>
                  <div className="text-xs text-zinc-600">No pending jobs</div>
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                {sortedQueues.map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2">
                    <div className="w-20 shrink-0 truncate text-xs text-zinc-400">{k}</div>
                    <div className="relative flex-1 h-1.5 rounded-full bg-zinc-800">
                      <div
                        className={cn("h-full rounded-full transition-all duration-500", depthColor(v))}
                        style={{ width: `${Math.max(4, (v / maxDepth) * 100)}%` }}
                      />
                    </div>
                    <div className={cn("w-6 text-right text-xs font-bold tabular-nums", depthTextColor(v))}>
                      {v}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
