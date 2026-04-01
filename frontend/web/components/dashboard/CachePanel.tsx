"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#22d3ee", "#27272a"];

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
  const pie = [
    { name: "Hit", value: Math.max(0, rate) },
    { name: "Miss", value: Math.max(0, 100 - rate) },
  ];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-50">Cache stats</div>
          <div className="text-xs text-zinc-400">Hit rate + counts</div>
        </div>
        <LiveIndicator ok={!error} label={!error ? "Live" : "Degraded"} />
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-4 w-44" />
          <Skeleton className="h-4 w-52" />
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
        <div className="grid grid-cols-2 gap-4">
          <div className="h-28">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  contentStyle={{
                    background: "rgba(9, 9, 11, 0.95)",
                    border: "1px solid rgba(63, 63, 70, 0.6)",
                    color: "#fafafa",
                    fontSize: 12,
                  }}
                />
                <Pie
                  data={pie}
                  dataKey="value"
                  innerRadius={34}
                  outerRadius={48}
                  paddingAngle={2}
                  stroke="rgba(0,0,0,0)"
                >
                  {pie.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col justify-center">
            <div className="text-2xl font-semibold text-zinc-50">
              {cacheHitRatePercent !== null ? `${rate.toFixed(2)}%` : "—"}
            </div>
            <div className="mt-2 space-y-1 text-sm text-zinc-200">
              <div className="flex items-center justify-between">
                <span>Hits</span>
                <span className="font-medium text-zinc-50">{hits ?? "—"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Misses</span>
                <span className="font-medium text-zinc-50">{misses ?? "—"}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

