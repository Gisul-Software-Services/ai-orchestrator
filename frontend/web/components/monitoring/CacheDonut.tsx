"use client";

import { useMemo, useState } from "react";
import { Pie, PieChart, ResponsiveContainer, Cell } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { adminFetchJson } from "@/lib/adminApi";

type InferenceSnapshot = {
  cache_hits?: number;
  cache_misses?: number;
  cache_hit_rate_percent?: number;
};

function asInt(v: unknown): number {
  if (typeof v === "number" && Number.isFinite(v)) return Math.trunc(v);
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) {
    return Math.trunc(Number(v));
  }
  return 0;
}

export function CacheDonut({ snapshot }: { snapshot: InferenceSnapshot | null }) {
  const hits = asInt(snapshot?.cache_hits);
  const misses = asInt(snapshot?.cache_misses);
  const total = Math.max(1, hits + misses);
  const hitRate =
    typeof snapshot?.cache_hit_rate_percent === "number"
      ? snapshot.cache_hit_rate_percent
      : Math.round((100 * hits) / total * 100) / 100;

  const [clearing, setClearing] = useState(false);
  const [localZeroed, setLocalZeroed] = useState(false);

  const chartData = useMemo(() => {
    if (localZeroed) {
      return [
        { name: "Hits", value: 0 },
        { name: "Misses", value: 0 },
      ];
    }
    return [
      { name: "Hits", value: hits },
      { name: "Misses", value: misses },
    ];
  }, [hits, misses, localZeroed]);

  async function clearCache() {
    setClearing(true);
    try {
      await adminFetchJson("/api/admin/cache/clear", { method: "POST" });
      toast.success("Cache cleared successfully");
      setLocalZeroed(true);
      // Let the next polling snapshot repopulate naturally.
      window.setTimeout(() => setLocalZeroed(false), 10_000);
    } catch {
      toast.error("Failed to clear cache");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm text-zinc-200">Cache</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {Number.isFinite(hitRate) ? `${hitRate.toFixed(2)}%` : "—"}
          </div>
          <div className="mt-1 text-xs text-zinc-500">Hit rate</div>
        </div>
        <Button
          variant="outline"
          onClick={clearCache}
          disabled={clearing}
          className="border-white/10"
        >
          {clearing ? "Clearing…" : "Clear Cache"}
        </Button>
      </div>

      <div className="mt-4 h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              innerRadius={64}
              outerRadius={92}
              paddingAngle={2}
              isAnimationActive={false}
            >
              <Cell fill="#22c55e" />
              <Cell fill="#ef4444" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/5">
          <div className="text-xs text-zinc-500">Hits</div>
          <div className="mt-1 font-semibold tabular-nums">{localZeroed ? 0 : hits}</div>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/5">
          <div className="text-xs text-zinc-500">Misses</div>
          <div className="mt-1 font-semibold tabular-nums">
            {localZeroed ? 0 : misses}
          </div>
        </div>
        <div className="col-span-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-white/10 dark:bg-white/5">
          <div className="text-xs text-zinc-500">Cache size (entries)</div>
          <div className="mt-1 font-semibold tabular-nums">—</div>
        </div>
      </div>
    </div>
  );
}

