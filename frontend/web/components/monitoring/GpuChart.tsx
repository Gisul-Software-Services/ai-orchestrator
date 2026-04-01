"use client";

import { MetricThresholdChart, type Threshold } from "@/components/monitoring/MetricThresholdChart";

type Point = {
  timestamp: number;
  vram_percent: number | null;
  gpu_utilization: number | null;
  temperature_c: number | null;
  power_watts: number | null;
};

type Status = "healthy" | "warning" | "critical" | "unknown";

function statusColor(s: Status) {
  if (s === "critical") return "#ef4444";
  if (s === "warning") return "#f59e0b";
  return "#22c55e";
}

function getStatus(value: number | null, warn?: number, crit?: number): Status {
  if (value === null || !Number.isFinite(value)) return "unknown";
  if (crit !== undefined && value >= crit) return "critical";
  if (warn !== undefined && value >= warn) return "warning";
  return "healthy";
}

function fmtNumber(
  v: number | null,
  opts?: { unit?: string; digits?: number }
) {
  if (v === null || !Number.isFinite(v)) return "—";
  const d = opts?.digits ?? 0;
  return `${v.toFixed(d)}${opts?.unit ?? ""}`;
}

export function GpuChart({
  title,
  data,
  metric,
  unit,
  yDomain,
  warnAt,
  criticalAt,
  thresholds,
  digits = 0,
  unavailableMessage,
}: {
  title: string;
  data: Point[];
  metric: keyof Pick<
    Point,
    "vram_percent" | "gpu_utilization" | "temperature_c" | "power_watts"
  >;
  unit?: string;
  yDomain?: any;
  warnAt?: number;
  criticalAt?: number;
  thresholds?: Threshold[];
  digits?: number;
  unavailableMessage?: string | null;
}) {
  const latest = data.at(-1)?.[metric] ?? null;
  const s = getStatus(
    typeof latest === "number" ? latest : null,
    warnAt,
    criticalAt
  );
  const lineColor = s === "unknown" ? "rgba(255,255,255,0.25)" : statusColor(s);

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm text-zinc-200">{title}</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {fmtNumber(typeof latest === "number" ? latest : null, {
              unit,
              digits,
            })}
          </div>
        </div>
        {unavailableMessage ? (
          <div className="max-w-[180px] text-right text-xs text-zinc-500">
            {unavailableMessage}
          </div>
        ) : null}
      </div>
      <div className="mt-3">
        <MetricThresholdChart
          data={data}
          dataKey={metric}
          unit={unit}
          height={200}
          yDomain={yDomain}
          thresholds={thresholds}
          lineColor={lineColor}
          valueFormatter={(v) => fmtNumber(v, { unit, digits })}
        />
      </div>
    </div>
  );
}

