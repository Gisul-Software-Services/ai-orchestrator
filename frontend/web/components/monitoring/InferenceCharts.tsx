"use client";

import { MetricThresholdChart } from "@/components/monitoring/MetricThresholdChart";
import { cn } from "@/lib/utils";

type InferencePoint = {
  timestamp: number;
  avg_latency_seconds: number | null;
  total_requests: number;
  errors: number;
  cache_hit_rate_percent: number | null;
};

type LatencyMsPoint   = { timestamp: number; avg_latency_ms: number | null };
type RequestRatePoint = { timestamp: number; requests_per_window: number };
type CacheRatePoint   = { timestamp: number; cache_hit_rate_percent: number | null };

function fmt(v: number | null, digits = 0, unit?: string) {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(digits)}${unit ?? ""}`;
}

function latencyStatus(ms: number | null): "good" | "warn" | "bad" | "none" {
  if (ms === null) return "none";
  if (ms < 500)  return "good";
  if (ms < 2000) return "warn";
  return "bad";
}

export function InferenceCharts({ data }: { data: InferencePoint[] }) {
  const latencyMs: LatencyMsPoint[] = data.map((p) => ({
    timestamp: p.timestamp,
    avg_latency_ms: p.avg_latency_seconds !== null ? p.avg_latency_seconds * 1000 : null,
  }));

  const requestRate: RequestRatePoint[] = data.map((p, idx) => {
    const prev = idx > 0 ? data[idx - 1] : null;
    const delta = prev ? p.total_requests - prev.total_requests : 0;
    return { timestamp: p.timestamp, requests_per_window: Math.max(0, delta) };
  });

  const cacheRate: CacheRatePoint[] = data.map((p) => ({
    timestamp: p.timestamp,
    cache_hit_rate_percent: p.cache_hit_rate_percent,
  }));

  // Only show cache quality badge when there are actual requests
  const maxRequests = data.reduce((s, p) => Math.max(s, p.total_requests), 0);
  const hasRequests = maxRequests > 0;

  const latestLatencyMs = latencyMs.at(-1)?.avg_latency_ms ?? null;
  const latestRate      = requestRate.at(-1)?.requests_per_window ?? 0;
  const latestCache     = hasRequests ? (cacheRate.at(-1)?.cache_hit_rate_percent ?? null) : null;

  const ls = latencyStatus(latestLatencyMs);
  const latencyColor     = ls === "good" ? "#34d399" : ls === "warn" ? "#fbbf24" : ls === "bad" ? "#f87171" : "#22d3ee";
  const latencyTextColor = ls === "good" ? "text-emerald-400" : ls === "warn" ? "text-amber-400" : ls === "bad" ? "text-red-400" : "text-console-accent";
  const latencyBorder    = ls === "good" ? "border-emerald-500/20" : ls === "warn" ? "border-amber-500/20" : ls === "bad" ? "border-red-500/20" : "border-zinc-800/60";

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">

      {/* Latency */}
      <div className={cn("relative overflow-hidden rounded-xl border bg-zinc-900/50 p-5 backdrop-blur-sm", latencyBorder)}>
        <div className="absolute inset-x-0 top-0 h-0.5 opacity-70"
          style={{ background: `linear-gradient(90deg,transparent,${latencyColor},transparent)` }} />
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-zinc-500">Avg Latency</div>
        <div className={cn("text-4xl font-bold tabular-nums tracking-tight", latencyTextColor)}>
          {fmt(latestLatencyMs, 0, " ms")}
        </div>
        <div className="mt-1">
          <span className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium",
            ls === "good" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            : ls === "warn" ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
            : ls === "bad"  ? "border-red-500/30 bg-red-500/10 text-red-300"
            : "border-zinc-700 bg-zinc-800 text-zinc-500"
          )}>
            {ls === "good" ? "Fast" : ls === "warn" ? "Slow" : ls === "bad" ? "Very slow" : "No data"}
          </span>
        </div>
        <div className="mt-4">
          <MetricThresholdChart
            data={latencyMs} dataKey="avg_latency_ms" unit=" ms" height={160}
            lineColor={latencyColor}
            thresholds={[
              { value: 500,  color: "#f59e0b", label: "500ms" },
              { value: 2000, color: "#ef4444", label: "2s" },
            ]}
            valueFormatter={(v) => fmt(v, 0, " ms")}
          />
        </div>
      </div>

      {/* Request rate */}
      <div className="relative overflow-hidden rounded-xl border border-violet-500/20 bg-zinc-900/50 p-5 backdrop-blur-sm">
        <div className="absolute inset-x-0 top-0 h-0.5 opacity-70 bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-zinc-500">Request Rate</div>
        <div className="text-4xl font-bold tabular-nums tracking-tight text-console-violet">
          {latestRate}
          <span className="ml-1.5 text-lg font-normal text-zinc-500">/ 5s</span>
        </div>
        <div className="mt-1">
          <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-300">
            {latestRate === 0 ? "Idle" : latestRate < 5 ? "Low" : latestRate < 20 ? "Moderate" : "High"}
          </span>
        </div>
        <div className="mt-4">
          <MetricThresholdChart
            data={requestRate} dataKey="requests_per_window" height={160}
            lineColor="#a78bfa"
            valueFormatter={(v) => (v === null ? "—" : `${Math.round(v)}/5s`)}
          />
        </div>
      </div>

      {/* Cache hit rate */}
      <div className="relative overflow-hidden rounded-xl border border-emerald-500/20 bg-zinc-900/50 p-5 backdrop-blur-sm">
        <div className="absolute inset-x-0 top-0 h-0.5 opacity-70 bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-zinc-500">Cache Hit Rate</div>
        <div className="text-4xl font-bold tabular-nums tracking-tight text-console-emerald">
          {latestCache != null ? `${latestCache.toFixed(1)}%` : "—"}
        </div>
        <div className="mt-1">
          <span className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium",
            latestCache == null
              ? "border-zinc-700 bg-zinc-800 text-zinc-500"
              : latestCache > 70
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : latestCache > 40
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  : "border-red-500/30 bg-red-500/10 text-red-300"
          )}>
            {latestCache == null ? "No data" : latestCache > 70 ? "Excellent" : latestCache > 40 ? "Fair" : "Poor"}
          </span>
        </div>
        <div className="mt-4">
          <MetricThresholdChart
            data={cacheRate} dataKey="cache_hit_rate_percent" unit="%" height={160}
            yDomain={[0, 100]} lineColor="#34d399"
            thresholds={[{ value: 70, color: "#34d399", label: "70%" }]}
            valueFormatter={(v) => fmt(v, 1, "%")}
          />
        </div>
      </div>

    </div>
  );
}
