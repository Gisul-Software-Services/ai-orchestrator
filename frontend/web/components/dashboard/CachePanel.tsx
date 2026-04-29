"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

export function CachePanel({
  loading,
  error,
  lastOkAt,
  cacheHitRatePercent,
  hits,
  misses,
}: {
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  cacheHitRatePercent: number | null;
  hits: number | null;
  misses: number | null;
}) {
  const rate = cacheHitRatePercent ?? 0;
  const isEmpty = (hits === null || hits === 0) && (misses === null || misses === 0);

  const pie = [
    { name: "Hit", value: Math.max(0, rate) },
    { name: "Miss", value: Math.max(0, 100 - rate) },
  ];

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-100">Cache stats</div>
          <div className="text-xs text-zinc-500">Hit rate + counts</div>
        </div>
        <LiveIndicator ok={!error} label={!error ? "Live" : "Degraded"} />
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-4 w-44" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">
          <div className="font-medium">Service unreachable</div>
          <div className="mt-1 text-xs text-amber-300/70">
            Last fetch: {lastOkAt ? new Date(lastOkAt).toLocaleString() : "never"}
          </div>
        </div>
      ) : isEmpty ? (
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-zinc-800 bg-zinc-900/60">
            <span className="text-2xl">📭</span>
          </div>
          <div className="text-sm font-medium text-zinc-400">No cache data yet</div>
          <div className="text-xs text-zinc-600">Stats appear once requests are made</div>
        </div>
      ) : (
        <div className="flex items-center gap-4">
          {/* Donut */}
          <div className="relative h-28 w-28 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pie}
                  dataKey="value"
                  innerRadius={38}
                  outerRadius={52}
                  paddingAngle={3}
                  startAngle={90}
                  endAngle={-270}
                  stroke="none"
                >
                  <Cell fill="#22d3ee" />
                  <Cell fill="#27272a" />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-lg font-bold text-zinc-50">
                {rate.toFixed(0)}%
              </div>
              <div className="text-[9px] text-zinc-600">hit rate</div>
            </div>
          </div>

          {/* Stats */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-console-accent" />
                <span className="text-xs text-zinc-400">Hits</span>
              </div>
              <span className="text-sm font-bold text-zinc-100 tabular-nums">
                {hits?.toLocaleString() ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-zinc-600" />
                <span className="text-xs text-zinc-400">Misses</span>
              </div>
              <span className="text-sm font-bold text-zinc-100 tabular-nums">
                {misses?.toLocaleString() ?? "—"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
