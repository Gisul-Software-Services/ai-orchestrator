"use client";

import { useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { adminFetchJson } from "@/lib/adminApi";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

type InferenceSnapshot = {
  cache_hits?: number;
  cache_misses?: number;
  cache_hit_rate_percent?: number;
};

function asInt(v: unknown): number {
  if (typeof v === "number" && Number.isFinite(v)) return Math.trunc(v);
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)))
    return Math.trunc(Number(v));
  return 0;
}

export function CacheDonut({ snapshot }: { snapshot: InferenceSnapshot | null }) {
  const hits   = asInt(snapshot?.cache_hits);
  const misses = asInt(snapshot?.cache_misses);
  const total  = hits + misses;

  const hitRate =
    typeof snapshot?.cache_hit_rate_percent === "number"
      ? snapshot.cache_hit_rate_percent
      : total > 0
        ? (100 * hits) / total
        : 0;

  const [clearing, setClearing] = useState(false);
  const [localZeroed, setLocalZeroed] = useState(false);

  // Always show a ring — use placeholder when empty
  const chartData = useMemo(() => {
    if (localZeroed || total === 0) {
      // Show a faint placeholder ring
      return [{ name: "Empty", value: 1, placeholder: true }];
    }
    return [
      { name: "Hits",   value: hits,   placeholder: false },
      { name: "Misses", value: misses, placeholder: false },
    ];
  }, [hits, misses, total, localZeroed]);

  const isEmpty = total === 0 || localZeroed;

  async function clearCache() {
    setClearing(true);
    try {
      await adminFetchJson("/api/admin/cache/clear", { method: "POST" });
      toast.success("Cache cleared");
      setLocalZeroed(true);
      window.setTimeout(() => setLocalZeroed(false), 10_000);
    } catch {
      toast.error("Failed to clear cache");
    } finally {
      setClearing(false);
    }
  }

  const rateColor =
    isEmpty ? "text-zinc-500"
    : hitRate >= 70 ? "text-console-emerald"
    : hitRate >= 40 ? "text-amber-400"
    : "text-red-400";

  const rateLabel =
    isEmpty ? "No data"
    : hitRate >= 70 ? "Excellent"
    : hitRate >= 40 ? "Fair"
    : "Poor";

  const rateBadge =
    isEmpty ? "border-zinc-700/60 bg-zinc-800/60 text-zinc-500"
    : hitRate >= 70 ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
    : hitRate >= 40 ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
    : "border-red-500/30 bg-red-500/10 text-red-300";

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5 backdrop-blur-sm">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-zinc-100">Cache</div>
          <div className="text-xs text-zinc-600">Hit / miss breakdown</div>
        </div>
        <Button
          variant="outline"
          className="h-8 border-red-500/20 bg-red-500/5 px-3 text-xs text-red-400 hover:bg-red-500/10 hover:border-red-500/40"
          onClick={clearCache}
          disabled={clearing}
        >
          <Trash2 className="mr-1.5 h-3 w-3" />
          {clearing ? "Clearing…" : "Clear Cache"}
        </Button>
      </div>

      {/* Donut + center */}
      <div className="flex items-center gap-6">
        <div className="relative h-[160px] w-[160px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                innerRadius={52}
                outerRadius={72}
                paddingAngle={isEmpty ? 0 : 3}
                startAngle={90}
                endAngle={-270}
                isAnimationActive={false}
                stroke="none"
              >
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      (entry as any).placeholder
                        ? "rgba(255,255,255,0.06)"
                        : i === 0
                          ? "#34d399"
                          : "#f87171"
                    }
                  />
                ))}
              </Pie>
              {!isEmpty && (
                <Tooltip
                  contentStyle={{
                    background: "rgba(9,9,11,0.95)",
                    border: "1px solid rgba(63,63,70,0.8)",
                    borderRadius: 10,
                    fontSize: 12,
                    color: "#fafafa",
                  }}
                  formatter={(v: number, name: string) => [v.toLocaleString(), name]}
                />
              )}
            </PieChart>
          </ResponsiveContainer>

          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <div className={cn("text-2xl font-bold tabular-nums leading-none", rateColor)}>
              {isEmpty ? "—" : `${hitRate.toFixed(0)}%`}
            </div>
            <div className="mt-1 text-[10px] text-zinc-600">hit rate</div>
          </div>
        </div>

        {/* Right stats */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center justify-between">
            <span className={cn("rounded-full border px-2.5 py-1 text-[11px] font-medium", rateBadge)}>
              {rateLabel}
            </span>
            <span className="text-xs text-zinc-600">
              {total > 0 ? `${total.toLocaleString()} total` : "No requests yet"}
            </span>
          </div>

          {/* Hit bar */}
          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-zinc-400">Hits</span>
              </div>
              <span className="font-bold tabular-nums text-emerald-400">
                {localZeroed ? 0 : hits.toLocaleString()}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-emerald-400 transition-all duration-700"
                style={{ width: total > 0 && !localZeroed ? `${(hits / total) * 100}%` : "0%" }}
              />
            </div>
          </div>

          {/* Miss bar */}
          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-400" />
                <span className="text-zinc-400">Misses</span>
              </div>
              <span className="font-bold tabular-nums text-red-400">
                {localZeroed ? 0 : misses.toLocaleString()}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-red-400 transition-all duration-700"
                style={{ width: total > 0 && !localZeroed ? `${(misses / total) * 100}%` : "0%" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
