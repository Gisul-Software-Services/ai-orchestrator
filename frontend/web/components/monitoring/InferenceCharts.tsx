"use client";

import { MetricThresholdChart } from "@/components/monitoring/MetricThresholdChart";

type InferencePoint = {
  timestamp: number;
  avg_latency_seconds: number | null;
  total_requests: number;
  errors: number;
};

function fmt(v: number | null, digits = 2, unit?: string) {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(digits)}${unit ?? ""}`;
}

export function InferenceCharts({ data }: { data: InferencePoint[] }) {
  const requestRate = data.map((p, idx) => {
    const prev = idx > 0 ? data[idx - 1] : null;
    const delta = prev ? p.total_requests - prev.total_requests : 0;
    return { timestamp: p.timestamp, requests_per_window: Math.max(0, delta) };
  });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">Average Latency (seconds)</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">
          {fmt(data.at(-1)?.avg_latency_seconds ?? null, 3, "s")}
        </div>
        <div className="mt-3">
          <MetricThresholdChart
            data={data}
            dataKey={"avg_latency_seconds"}
            unit="s"
            height={200}
            lineColor="#38bdf8"
            valueFormatter={(v) => fmt(v, 3, "s")}
          />
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">Request Rate (per 5s)</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">
          {requestRate.at(-1)?.requests_per_window ?? 0}
        </div>
        <div className="mt-3">
          <MetricThresholdChart
            data={requestRate}
            dataKey={"requests_per_window"}
            height={200}
            lineColor="#22c55e"
            valueFormatter={(v) => (v === null ? "—" : `${Math.round(v)}`)}
          />
        </div>
      </div>
    </div>
  );
}

