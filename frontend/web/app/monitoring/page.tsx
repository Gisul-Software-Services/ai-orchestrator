"use client";

import { format } from "date-fns";
import {
  Activity,
  AlertTriangle,
  Cpu,
  Database,
  RefreshCw,
} from "lucide-react";
import { LiveIndicator } from "@/components/dashboard/LiveIndicator";
import { CacheDonut } from "@/components/monitoring/CacheDonut";
import { GpuChart } from "@/components/monitoring/GpuChart";
import { InferenceCharts } from "@/components/monitoring/InferenceCharts";
import { QueueChart } from "@/components/monitoring/QueueChart";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetricsHistory } from "@/hooks/useMetricsHistory";
import { useStatsQuery } from "@/hooks/useMetrics";
import { cn } from "@/lib/utils";

function asNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
  return null;
}
function asInt(v: unknown): number {
  const n = asNumber(v);
  return n === null ? 0 : Math.trunc(n);
}
function fmtPct(v: number | null) {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(1)}%`;
}
function depthStatus(n: number): "ok" | "warn" | "crit" {
  if (n <= 0) return "ok";
  if (n <= 5) return "warn";
  return "crit";
}

// ── Stat pill ─────────────────────────────────────────────────────────────────
function StatPill({
  label,
  value,
  color = "zinc",
}: {
  label: string;
  value: string;
  color?: "cyan" | "violet" | "emerald" | "red" | "amber" | "zinc";
}) {
  const cls = {
    cyan:    "text-console-accent",
    violet:  "text-console-violet",
    emerald: "text-console-emerald",
    red:     "text-red-400",
    amber:   "text-amber-400",
    zinc:    "text-zinc-400",
  }[color];
  return (
    <div className="flex items-center gap-2 rounded-lg border border-zinc-800/60 bg-zinc-900/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-zinc-600">{label}</div>
      <div className={cn("ml-auto text-sm font-bold tabular-nums", cls)}>{value}</div>
    </div>
  );
}

// ── Section divider ───────────────────────────────────────────────────────────
function Section({
  icon: Icon,
  title,
  subtitle,
  badge,
  children,
}: {
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800/60 bg-gradient-to-br from-zinc-900 to-zinc-800">
            <Icon className="h-4 w-4 text-console-accent" strokeWidth={1.75} />
          </div>
          <div>
            <div className="text-lg font-bold text-zinc-50">{title}</div>
            {subtitle && <div className="text-xs text-zinc-600">{subtitle}</div>}
          </div>
        </div>
        {badge}
      </div>
      {children}
    </section>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function MonitoringPage() {
  const { gpuHistory, inferenceHistory, queueHistory, gpuQuery, inferenceQuery, queuesQuery } =
    useMetricsHistory();
  const statsQuery = useStatsQuery();

  const gpuAvailable = gpuQuery.data?.available !== false;
  const gpuError = gpuQuery.data?.error as string | null | undefined;
  const gpu = gpuQuery.data ?? null;
  const usedGb = gpu?.memory_used_gb ?? null;
  const totalGb = gpu?.memory_total_gb ?? null;
  const powerW = gpu?.power_watts ?? null;

  const anyError =
    Boolean(gpuQuery.error) || Boolean(inferenceQuery.error) ||
    Boolean(queuesQuery.error) || Boolean(statsQuery.error);

  const lastUpdatedAt = Math.max(
    gpuQuery.dataUpdatedAt ?? 0,
    inferenceQuery.dataUpdatedAt ?? 0,
    queuesQuery.dataUpdatedAt ?? 0,
    statsQuery.dataUpdatedAt ?? 0
  );
  const stale = !lastUpdatedAt || Date.now() - lastUpdatedAt > 15_000 || anyError;

  const activeJobs  = asInt((queuesQuery.data as any)?.active_jobs);
  const jobsInStore = asInt((queuesQuery.data as any)?.jobs_in_store);

  const hasGpuHistory       = gpuHistory.length > 0;
  const hasInferenceHistory = inferenceHistory.length > 0;
  const hasQueueHistory     = queueHistory.length > 0;

  // Inference-derived stats
  const cacheHits    = (inferenceQuery.data as any)?.cache_hits ?? null;
  const cacheMisses  = (inferenceQuery.data as any)?.cache_misses ?? null;
  const totalRequests = cacheHits != null && cacheMisses != null ? cacheHits + cacheMisses : null;
  const cacheHitRate = totalRequests != null && totalRequests > 0
    ? (cacheHits / totalRequests) * 100
    : null;
  const avgBatchSize = (inferenceQuery.data as any)?.avg_batch_size ?? null;

  return (
    <div className="animate-fade-in space-y-10">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-3xl font-bold tracking-tight text-zinc-50">Monitoring</div>
          <div className="mt-1 text-sm text-zinc-500">
            Live system metrics · 5 s refresh · 5 min rolling window
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdatedAt > 0 && (
            <div className="flex items-center gap-1.5 rounded-full border border-zinc-800/60 bg-zinc-900/60 px-3 py-1.5 text-xs text-zinc-500">
              <RefreshCw className="h-3 w-3" />
              {format(new Date(lastUpdatedAt), "HH:mm:ss")}
            </div>
          )}
          <LiveIndicator ok={!stale} label={stale ? "Stale" : "Live"} />
        </div>
      </div>

      {/* ── Error banner ───────────────────────────────────────────────────── */}
      {anyError && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          Model-service appears unreachable. Showing last known data where available.
        </div>
      )}

      {/* ── GPU & Hardware ─────────────────────────────────────────────────── */}
      <Section
        icon={Cpu}
        title="GPU & Hardware"
        subtitle="NVML snapshot — sampled every 5 s"
        badge={
          !gpuAvailable && gpuQuery.isSuccess ? (
            <div className="rounded-full border border-amber-500/20 bg-amber-500/5 px-3 py-1 text-[11px] text-amber-400">
              {gpuError ?? "NVML unavailable"}
            </div>
          ) : undefined
        }
      >
        {!hasGpuHistory && gpuQuery.isLoading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[1,2,3,4].map(i => <Skeleton key={i} className="h-[300px] rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <GpuChart
              title="VRAM Usage"
              data={gpuHistory}
              metric="vram_percent"
              unit="%"
              yDomain={[0, 100]}
              warnAt={70}
              criticalAt={90}
              thresholds={[
                { value: 70, color: "#f59e0b", label: "70%" },
                { value: 90, color: "#ef4444", label: "90%" },
              ]}
              unavailableMessage={!gpuAvailable ? gpuError ?? "Unavailable" : null}
            />
            <GpuChart
              title="GPU Utilisation"
              data={gpuHistory}
              metric="gpu_utilization"
              unit="%"
              yDomain={[0, 100]}
              unavailableMessage={!gpuAvailable ? gpuError ?? "Unavailable" : null}
            />
            <GpuChart
              title="Temperature"
              data={gpuHistory}
              metric="temperature_c"
              unit="°C"
              yDomain={[0, 110]}
              warnAt={70}
              criticalAt={85}
              thresholds={[
                { value: 70, color: "#f59e0b", label: "70°C" },
                { value: 85, color: "#ef4444", label: "85°C" },
              ]}
              unavailableMessage={!gpuAvailable ? gpuError ?? "Unavailable" : null}
            />
            {gpuHistory.some((p) => typeof p.power_watts === "number") ? (
              <GpuChart
                title="Power Draw"
                data={gpuHistory}
                metric="power_watts"
                unit=" W"
                digits={0}
                unavailableMessage={!gpuAvailable ? gpuError ?? "Unavailable" : null}
              />
            ) : (
              <div className="flex flex-col gap-3 rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5">
                <div className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Power Draw</div>
                <div className="text-3xl font-bold text-zinc-700">N/A</div>
                <div className="text-xs text-zinc-700">Power data unavailable from NVML</div>
                <div className="mt-auto h-[140px] rounded-lg bg-zinc-800/20" />
              </div>
            )}
          </div>
        )}

        {/* GPU detail strip */}
        {gpuAvailable && gpu && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatPill label="VRAM used" value={usedGb != null ? `${usedGb.toFixed(2)} GB` : "—"} color="emerald" />
            <StatPill label="VRAM total" value={totalGb != null ? `${totalGb.toFixed(2)} GB` : "—"} color="zinc" />
            <StatPill label="NVML status" value={gpu.available ? "OK" : "Error"} color={gpu.available ? "emerald" : "red"} />
            <StatPill label="Power" value={powerW != null ? `${powerW.toFixed(1)} W` : "—"} color="violet" />
          </div>
        )}
      </Section>

      {/* ── Inference Metrics ──────────────────────────────────────────────── */}
      <Section
        icon={Activity}
        title="Inference Metrics"
        subtitle="Latency · request rate · cache — rolling 5 min window"
      >
        {/* Inference charts only — no static KPI strip */}
        {!hasInferenceHistory && inferenceQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {[1,2,3].map(i => <Skeleton key={i} className="h-[280px] rounded-xl" />)}
          </div>
        ) : (
          <InferenceCharts data={inferenceHistory as any} />
        )}
      </Section>

      {/* ── Queue Status ───────────────────────────────────────────────────── */}
      <Section
        icon={Database}
        title="Queue Status"
        subtitle="Batch queue depths — rolling 5 min window"
        badge={
          <div className="flex items-center gap-3 text-xs">
            <span className="rounded-full border border-zinc-800/60 bg-zinc-900/60 px-2.5 py-1 text-zinc-400">
              Active: <span className="font-bold text-zinc-200">{activeJobs}</span>
            </span>
            <span className="rounded-full border border-zinc-800/60 bg-zinc-900/60 px-2.5 py-1 text-zinc-400">
              Stored: <span className="font-bold text-zinc-200">{jobsInStore}</span>
            </span>
          </div>
        }
      >
        {!hasQueueHistory && queuesQuery.isLoading ? (
          <Skeleton className="h-[260px] rounded-xl" />
        ) : (
          <QueueChart data={queueHistory as any} />
        )}
      </Section>

      {/* ── Cache ──────────────────────────────────────────────────────────── */}
      <Section
        icon={Database}
        title="Cache"
        subtitle="Hit/miss breakdown · clear action"
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Donut */}
          <CacheDonut snapshot={(inferenceQuery.data ?? null) as any} />

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3 content-start">
            {[
              {
                label: "Cache hits",
                value: inferenceQuery.data != null
                  ? (inferenceQuery.data.cache_hits ?? 0).toLocaleString()
                  : "—",
                color: "emerald" as const,
              },
              {
                label: "Cache misses",
                value: inferenceQuery.data != null
                  ? (inferenceQuery.data.cache_misses ?? 0).toLocaleString()
                  : "—",
                color: "red" as const,
              },
              {
                label: "Hit rate (stats)",
                value: cacheHitRate != null ? fmtPct(cacheHitRate) : "—",
                color: (cacheHitRate ?? 0) >= 60 ? "emerald" as const : "amber" as const,
              },
              {
                label: "Hit rate (live)",
                value: inferenceQuery.data != null
                  ? fmtPct(inferenceQuery.data.cache_hit_rate_percent ?? 0)
                  : "—",
                color: "cyan" as const,
              },
              {
                label: "Total requests",
                value: totalRequests != null ? totalRequests.toLocaleString() : "—",
                color: "violet" as const,
              },
              {
                label: "Avg batch size",
                value: avgBatchSize != null ? String(avgBatchSize) : "—",
                color: "zinc" as const,
              },
            ].map((item) => {
              const textCls = {
                emerald: "text-console-emerald", red: "text-red-400",
                amber: "text-amber-400", cyan: "text-console-accent",
                violet: "text-console-violet", zinc: "text-zinc-400",
              }[item.color];
              const borderCls = {
                emerald: "border-emerald-500/20", red: "border-red-500/20",
                amber: "border-amber-500/20", cyan: "border-cyan-500/20",
                violet: "border-violet-500/20", zinc: "border-zinc-800/60",
              }[item.color];
              return (
                <div key={item.label} className={cn("rounded-xl border bg-zinc-900/50 p-4", borderCls)}>
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">{item.label}</div>
                  <div className={cn("mt-2 text-2xl font-bold tabular-nums", textCls)}>{item.value}</div>
                </div>
              );
            })}
          </div>
        </div>
      </Section>

    </div>
  );
}
