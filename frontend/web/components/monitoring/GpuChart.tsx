"use client";

import { MetricThresholdChart, type Threshold } from "@/components/monitoring/MetricThresholdChart";
import { cn } from "@/lib/utils";

type Point = {
  timestamp: number;
  vram_percent: number | null;
  gpu_utilization: number | null;
  temperature_c: number | null;
  power_watts: number | null;
};

type Status = "healthy" | "warning" | "critical" | "unknown";

function getStatus(value: number | null, warn?: number, crit?: number): Status {
  if (value === null || !Number.isFinite(value)) return "unknown";
  if (crit !== undefined && value >= crit) return "critical";
  if (warn !== undefined && value >= warn) return "warning";
  return "healthy";
}

const statusConfig: Record<Status, {
  line: string;
  fill: string;
  text: string;
  border: string;
  bg: string;
  badge: string;
  dot: string;
}> = {
  healthy:  { line: "#34d399", fill: "rgba(52,211,153,0.15)",  text: "text-emerald-400", border: "border-emerald-500/25", bg: "bg-emerald-500/5",  badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-400" },
  warning:  { line: "#fbbf24", fill: "rgba(251,191,36,0.15)",  text: "text-amber-400",   border: "border-amber-500/25",   bg: "bg-amber-500/5",    badge: "bg-amber-500/15 text-amber-300 border-amber-500/30",     dot: "bg-amber-400" },
  critical: { line: "#f87171", fill: "rgba(248,113,113,0.15)", text: "text-red-400",     border: "border-red-500/25",     bg: "bg-red-500/5",      badge: "bg-red-500/15 text-red-300 border-red-500/30",           dot: "bg-red-400" },
  unknown:  { line: "#22d3ee", fill: "rgba(34,211,238,0.12)",  text: "text-cyan-400",    border: "border-zinc-800/60",    bg: "bg-zinc-900/50",    badge: "bg-zinc-800 text-zinc-400 border-zinc-700",              dot: "bg-zinc-500" },
};

function fmtNumber(v: number | null, opts?: { unit?: string; digits?: number }) {
  if (v === null || !Number.isFinite(v)) return "—";
  const d = opts?.digits ?? 0;
  return `${v.toFixed(d)}${opts?.unit ?? ""}`;
}

function statusLabel(s: Status) {
  if (s === "critical") return "Critical";
  if (s === "warning")  return "Warning";
  if (s === "healthy")  return "Normal";
  return "No data";
}

// Circular arc gauge using SVG
function ArcGauge({
  value,
  max = 100,
  color,
  size = 72,
}: {
  value: number | null;
  max?: number;
  color: string;
  size?: number;
}) {
  const r = (size - 8) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = -210;
  const sweepAngle = 240;

  function polarToXY(angle: number, radius: number) {
    const rad = ((angle - 90) * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  }

  function arcPath(startDeg: number, endDeg: number, r: number) {
    const s = polarToXY(startDeg, r);
    const e = polarToXY(endDeg, r);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
  }

  const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  const fillEnd = startAngle + (sweepAngle * pct) / 100;

  return (
    <svg width={size} height={size} className="shrink-0">
      {/* Track */}
      <path
        d={arcPath(startAngle, startAngle + sweepAngle, r)}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={6}
        strokeLinecap="round"
      />
      {/* Fill */}
      {value != null && pct > 0 && (
        <path
          d={arcPath(startAngle, fillEnd, r)}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 4px ${color}80)` }}
        />
      )}
    </svg>
  );
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
  metric: keyof Pick<Point, "vram_percent" | "gpu_utilization" | "temperature_c" | "power_watts">;
  unit?: string;
  yDomain?: [number, number];
  warnAt?: number;
  criticalAt?: number;
  thresholds?: Threshold[];
  digits?: number;
  unavailableMessage?: string | null;
}) {
  const latest = data.at(-1)?.[metric] ?? null;
  const numVal = typeof latest === "number" ? latest : null;
  const s = getStatus(numVal, warnAt, criticalAt);
  const cfg = statusConfig[s];

  // Gauge max: use yDomain upper bound or 100
  const gaugeMax = yDomain?.[1] ?? 100;

  return (
    <div className={cn(
      "relative overflow-hidden rounded-xl border p-5 backdrop-blur-sm transition-all",
      cfg.border, cfg.bg
    )}>
      {/* Top accent line */}
      <div
        className="absolute inset-x-0 top-0 h-0.5 opacity-70"
        style={{ background: `linear-gradient(90deg, transparent, ${cfg.line}, transparent)` }}
      />

      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{title}</div>
          {unavailableMessage ? (
            <div className="mt-1 text-xs text-zinc-600">{unavailableMessage}</div>
          ) : null}
        </div>
        <span className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
          cfg.badge
        )}>
          <span className={cn("h-1.5 w-1.5 rounded-full", cfg.dot)} />
          {statusLabel(s)}
        </span>
      </div>

      {/* Value + gauge row */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <ArcGauge value={numVal} max={gaugeMax} color={cfg.line} size={80} />
          {/* Center value inside gauge */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn("text-xs font-bold tabular-nums leading-none", cfg.text)}>
              {numVal != null ? `${numVal.toFixed(digits)}` : "—"}
            </span>
          </div>
        </div>
        <div>
          <div className={cn("text-3xl font-bold tabular-nums tracking-tight leading-none", cfg.text)}>
            {fmtNumber(numVal, { unit, digits })}
          </div>
          {thresholds && thresholds.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {thresholds.map((t) => (
                <span
                  key={t.value}
                  className="rounded border px-1.5 py-0.5 text-[10px] font-medium"
                  style={{ borderColor: `${t.color}40`, color: t.color, background: `${t.color}10` }}
                >
                  {t.label ?? `${t.value}${unit ?? ""}`}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="mt-4">
        <MetricThresholdChart
          data={data}
          dataKey={metric}
          unit={unit}
          height={140}
          yDomain={yDomain}
          thresholds={thresholds}
          lineColor={cfg.line}
          valueFormatter={(v) => fmtNumber(v, { unit, digits })}
        />
      </div>
    </div>
  );
}
