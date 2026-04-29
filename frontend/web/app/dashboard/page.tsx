"use client";

import {
  useHealthQuery,
  useMetricsInferenceQuery,
  useMetricsOverviewQuery,
  useMetricsQueuesQuery,
  useStatsQuery,
} from "@/hooks/useMetrics";
import { EndpointBarChart } from "@/components/dashboard/EndpointBarChart";
import { LiveIndicator } from "@/components/dashboard/LiveIndicator";
import type { InferenceMetrics, MetricsOverview, QueuesMetrics, StatsResponse } from "@/types/api";
import { Skeleton, DashboardSkeleton } from "@/components/ui/skeleton";
import {
  Activity, AlertTriangle, BarChart3, CheckCircle2,
  Cpu, Database, ExternalLink, MemoryStick, Server, Thermometer,
  TrendingUp, Zap, XCircle,
} from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import Link from "next/link";

// ── helpers ───────────────────────────────────────────────────────────────────
function sortEndpointCounts(m: Record<string, number> | undefined | null) {
  return Object.entries(m ?? {})
    .map(([endpoint, value]) => ({ endpoint, value }))
    .sort((a, b) => b.value - a.value);
}
function fmtMs(n: number | null) { return n != null ? `${n.toFixed(0)} ms` : "—"; }
function fmtPct(n: number | null) { return n != null ? `${n.toFixed(1)}%` : "—"; }
function fmtInt(n: number | null) { return n != null ? n.toLocaleString() : "—"; }
function gbFromMb(mb?: number | null) { return mb != null ? mb / 1024 : null; }

// ── Metric card ───────────────────────────────────────────────────────────────
type Accent = "cyan" | "violet" | "emerald" | "red" | "amber" | "zinc";

const ACCENT: Record<Accent, { border: string; text: string; top: string; icon: string }> = {
  cyan:    { border: "border-cyan-500/25",    text: "text-cyan-400",    top: "#22d3ee", icon: "text-cyan-500/60" },
  violet:  { border: "border-violet-500/25",  text: "text-violet-400",  top: "#a78bfa", icon: "text-violet-500/60" },
  emerald: { border: "border-emerald-500/25", text: "text-emerald-400", top: "#34d399", icon: "text-emerald-500/60" },
  red:     { border: "border-red-500/25",     text: "text-red-400",     top: "#f87171", icon: "text-red-500/60" },
  amber:   { border: "border-amber-500/25",   text: "text-amber-400",   top: "#fbbf24", icon: "text-amber-500/60" },
  zinc:    { border: "border-zinc-800/60",    text: "text-zinc-300",    top: "#52525b", icon: "text-zinc-600" },
};

function MetricCard({
  icon: Icon, label, value, sub, accent = "zinc", loading = false, large = false,
}: {
  icon: React.ElementType; label: string; value: string; sub?: string;
  accent?: Accent; loading?: boolean; large?: boolean;
}) {
  const a = ACCENT[accent];
  return (
    <div className={cn(
      "relative overflow-hidden rounded-2xl border bg-zinc-900/70 backdrop-blur-sm transition-all hover:bg-zinc-900/90",
      a.border, large ? "p-5" : "p-4"
    )}>
      <div className="absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg,transparent,${a.top}60,transparent)` }} />
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-zinc-600">{label}</span>
        <Icon className={cn("h-4 w-4", a.icon)} strokeWidth={1.5} />
      </div>
      {loading ? (
        <div className="space-y-2">
          <Skeleton className={cn("rounded-lg", large ? "h-10 w-36" : "h-8 w-28")} />
          <Skeleton className="h-3 w-20 rounded" />
        </div>
      ) : (
        <>
          <div className={cn("font-bold tabular-nums tracking-tight", a.text, large ? "text-4xl" : "text-2xl")}>
            {value}
          </div>
          {sub && <div className="mt-1 text-xs text-zinc-600">{sub}</div>}
        </>
      )}
    </div>
  );
}

// ── Panel wrapper ─────────────────────────────────────────────────────────────
function Panel({ title, sub, right, children, className }: {
  title: string; sub?: string; right?: React.ReactNode;
  children: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-zinc-800/60 bg-zinc-900/60 backdrop-blur-sm", className)}>
      <div className="flex items-center justify-between border-b border-zinc-800/60 px-5 py-3.5">
        <div>
          <div className="text-sm font-semibold text-zinc-100">{title}</div>
          {sub && <div className="text-xs text-zinc-600">{sub}</div>}
        </div>
        {right}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

// ── Queue depth bar ───────────────────────────────────────────────────────────
function QueueBar({ name, depth, max }: { name: string; depth: number; max: number }) {
  const isEmpty = depth === 0;
  const barColor = isEmpty ? "bg-zinc-800" : depth <= 5 ? "bg-emerald-400" : depth <= 20 ? "bg-amber-400" : "bg-red-400";
  const textColor = isEmpty ? "text-zinc-700" : depth <= 5 ? "text-emerald-400" : depth <= 20 ? "text-amber-400" : "text-red-400";
  const badgeColor = isEmpty
    ? "border-zinc-800/60 bg-zinc-900/40 text-zinc-600"
    : depth <= 5
      ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
      : depth <= 20
        ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
        : "border-red-500/20 bg-red-500/10 text-red-400";

  // Width: when all are 0, show a tiny 2% indicator so bars are visible
  const pct = max <= 0 ? 0 : (depth / max) * 100;
  const barWidth = isEmpty ? 0 : Math.max(3, pct);

  return (
    <div className="flex items-center gap-3 py-0.5">
      <span className="w-24 shrink-0 truncate font-mono text-xs text-zinc-400">{name}</span>
      <div className="relative flex-1 h-2 rounded-full bg-zinc-800/60">
        <div
          className={cn("h-full rounded-full transition-all duration-700", barColor)}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <span className={cn(
        "w-14 shrink-0 rounded-full border px-2 py-0.5 text-center text-xs font-bold tabular-nums",
        badgeColor
      )}>
        {depth}
      </span>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const healthQ   = useHealthQuery();
  const overviewQ = useMetricsOverviewQuery();
  const queuesQ   = useMetricsQueuesQuery();
  const inferenceQ = useMetricsInferenceQuery();
  const statsQ    = useStatsQuery();

  const unreachable = healthQ.isError || overviewQ.isError;
  const overview: MetricsOverview | undefined = overviewQ.data;
  const inferenceData: InferenceMetrics | undefined = inferenceQ.data;
  const queuesData: QueuesMetrics | undefined = queuesQ.data;
  const stats: StatsResponse | undefined = statsQ.data;

  const lastOkAt = Math.max(
    healthQ.isSuccess ? healthQ.dataUpdatedAt : 0,
    overviewQ.isSuccess ? overviewQ.dataUpdatedAt : 0,
    inferenceQ.isSuccess ? inferenceQ.dataUpdatedAt : 0,
    statsQ.isSuccess ? statsQ.dataUpdatedAt : 0,
  );
  const lastOk = lastOkAt > 0 ? lastOkAt : null;

  const modelLoaded = healthQ.data?.model_loaded ?? overview?.model_loaded ?? false;
  const gpu = overview?.gpu;
  const gpuOk = gpu?.available !== false;

  const usedGb  = gbFromMb(gpu?.memory_used_mb);
  const totalGb = gbFromMb(gpu?.memory_total_mb);
  const memPct  = gpu?.memory_used_percent ?? null;
  const utilPct = gpu?.gpu_util_percent ?? null;
  const tempC   = gpu?.temperature_c ?? null;
  const powerW  = gpu?.power_watts ?? null;

  const totalGenSec  = inferenceData?.total_generation_time_seconds;
  const totalReqs    = inferenceData?.total_requests;
  const errors       = inferenceData?.errors;
  const cacheHits    = inferenceData?.cache_hits;
  const cacheMisses  = inferenceData?.cache_misses;
  const cacheRate    = inferenceData?.cache_hit_rate_percent;

  const avgLatencyMs = totalGenSec != null && totalReqs != null && totalReqs > 0
    ? (totalGenSec / totalReqs) * 1000 : null;
  const errorRate = errors != null && totalReqs != null && totalReqs > 0
    ? (100 * errors) / totalReqs : null;

  const sortedQueues = Object.entries(queuesData?.queue_depths ?? {})
    .sort((a, b) => b[1] - a[1]);
  const maxDepth = Math.max(1, ...sortedQueues.map(([, v]) => v));

  const byEndpoint = sortEndpointCounts(stats?.requests_by_endpoint);

  const cacheIsEmpty = (cacheHits == null || cacheHits === 0) && (cacheMisses == null || cacheMisses === 0);
  const pieData = [
    { name: "Hit",  value: Math.max(0, cacheRate ?? 0) },
    { name: "Miss", value: Math.max(0, 100 - (cacheRate ?? 0)) },
  ];

  const loading = healthQ.isLoading || overviewQ.isLoading;

  // Show full skeleton on first load (no data yet)
  if (loading && !overview && !healthQ.data) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="animate-fade-in space-y-6">

      {/* ── Banners ─────────────────────────────────────────────────────────── */}
      {unreachable && (
        <div className="flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/5 px-5 py-3 text-sm text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span><span className="font-semibold">Service unreachable</span> — showing last known data.
            {lastOk && <span className="ml-2 text-amber-300/60">Last fetch: {format(new Date(lastOk), "HH:mm:ss")}</span>}
          </span>
        </div>
      )}
      {!modelLoaded && !unreachable && !loading && (
        <div className="flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/5 px-5 py-3 text-sm text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span><span className="font-semibold">Model not loaded</span> — generation endpoints unavailable.</span>
        </div>
      )}

      {/* ── Hero model status banner ─────────────────────────────────────────── */}
      <div className={cn(
        "relative overflow-hidden rounded-2xl border p-6",
        unreachable ? "border-zinc-800/60 bg-zinc-900/60"
        : modelLoaded ? "border-emerald-500/20 bg-emerald-500/5"
        : "border-red-500/20 bg-red-500/5"
      )}>
        <div className="absolute inset-x-0 top-0 h-px" style={{
          background: unreachable ? "linear-gradient(90deg,transparent,#52525b,transparent)"
          : modelLoaded ? "linear-gradient(90deg,transparent,#34d399,transparent)"
          : "linear-gradient(90deg,transparent,#f87171,transparent)"
        }} />
        {/* Glow blob */}
        <div className={cn(
          "absolute -right-20 -top-20 h-64 w-64 rounded-full blur-3xl opacity-10",
          modelLoaded && !unreachable ? "bg-emerald-400" : unreachable ? "bg-zinc-600" : "bg-red-400"
        )} />

        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className={cn(
              "flex h-14 w-14 items-center justify-center rounded-2xl border",
              unreachable ? "border-zinc-700/60 bg-zinc-800/60"
              : modelLoaded ? "border-emerald-500/30 bg-emerald-500/10"
              : "border-red-500/30 bg-red-500/10"
            )}>
              {unreachable ? (
                <XCircle className="h-7 w-7 text-zinc-500" strokeWidth={1.5} />
              ) : modelLoaded ? (
                <CheckCircle2 className="h-7 w-7 text-emerald-400" strokeWidth={1.5} />
              ) : (
                <XCircle className="h-7 w-7 text-red-400" strokeWidth={1.5} />
              )}
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Model Status</div>
              <div className={cn(
                "mt-0.5 text-3xl font-bold tracking-tight",
                unreachable ? "text-zinc-400" : modelLoaded ? "text-emerald-400" : "text-red-400"
              )}>
                {unreachable ? "UNREACHABLE" : modelLoaded ? "LOADED" : "NOT LOADED"}
              </div>
              {healthQ.data?.memory_gb != null && (
                <div className="mt-1 text-xs text-zinc-500">
                  {healthQ.data.memory_gb.toFixed(1)} GB system RAM
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">Active jobs</div>
              <div className="mt-0.5 text-xl font-bold text-zinc-100">{queuesData?.active_jobs ?? 0}</div>
            </div>
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">In store</div>
              <div className="mt-0.5 text-xl font-bold text-zinc-100">{queuesData?.jobs_in_store ?? 0}</div>
            </div>
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">Total requests</div>
              <div className="mt-0.5 text-xl font-bold text-cyan-400">{fmtInt(totalReqs ?? null)}</div>
            </div>
            <div className="flex items-center gap-2">
              <LiveIndicator ok={!unreachable} label={unreachable ? "Offline" : "Live"} />
            </div>
          </div>
        </div>
      </div>

      {/* ── GPU metrics row — 4 unique metrics, no duplication ──────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          icon={MemoryStick} label="GPU VRAM"
          value={gpuOk && usedGb != null && totalGb != null ? `${usedGb.toFixed(1)} / ${totalGb.toFixed(1)} GB` : "N/A"}
          sub={gpuOk && memPct != null ? `${memPct.toFixed(1)}% used` : gpu?.error ?? undefined}
          accent={!gpuOk ? "zinc" : memPct != null && memPct > 90 ? "red" : memPct != null && memPct > 70 ? "amber" : "emerald"}
          loading={loading}
        />
        <MetricCard
          icon={Zap} label="GPU Utilisation"
          value={gpuOk && utilPct != null ? `${utilPct.toFixed(0)}%` : "N/A"}
          sub={gpuOk && powerW != null ? `${powerW.toFixed(0)} W draw` : gpuOk ? "NVML OK" : undefined}
          accent={!gpuOk ? "zinc" : utilPct != null && utilPct > 90 ? "amber" : "cyan"}
          loading={loading}
        />
        <MetricCard
          icon={Thermometer} label="Temperature"
          value={gpuOk && tempC != null ? `${tempC.toFixed(0)}°C` : "N/A"}
          sub={gpuOk && tempC != null ? (tempC > 85 ? "Critical — check cooling" : tempC > 70 ? "Warm" : "Normal") : undefined}
          accent={!gpuOk ? "zinc" : tempC != null && tempC > 85 ? "red" : tempC != null && tempC > 70 ? "amber" : "emerald"}
          loading={loading}
        />
        <MetricCard
          icon={Activity} label="Avg Latency"
          value={fmtMs(avgLatencyMs)}
          sub={avgLatencyMs != null ? (avgLatencyMs < 500 ? "Fast" : avgLatencyMs < 2000 ? "Slow" : "Very slow") : totalReqs != null && totalReqs > 0 ? "Computing…" : "No requests yet"}
          accent={avgLatencyMs == null ? "zinc" : avgLatencyMs < 500 ? "emerald" : avgLatencyMs < 2000 ? "amber" : "red"}
          loading={loading}
        />
      </div>

      {/* ── Performance KPIs + quick nav ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard icon={TrendingUp} label="Total requests"
          value={fmtInt(totalReqs ?? null)} sub="All-time" accent="cyan" loading={inferenceQ.isLoading && !inferenceData} />
        <MetricCard icon={BarChart3} label="Error rate"
          value={fmtPct(errorRate)} sub={errors != null ? `${errors} errors` : undefined}
          accent={errorRate != null && errorRate > 5 ? "red" : errorRate != null && errorRate > 1 ? "amber" : "emerald"}
          loading={inferenceQ.isLoading && !inferenceData} />
        <MetricCard icon={Database} label="Cache hit rate"
          value={fmtPct(cacheRate ?? null)}
          sub={cacheHits != null ? `${fmtInt(cacheHits)} hits` : undefined}
          accent={cacheRate != null && cacheRate > 60 ? "emerald" : cacheRate != null ? "amber" : "zinc"}
          loading={inferenceQ.isLoading && !inferenceData} />
        <MetricCard icon={Server} label="Avg batch size"
          value={inferenceData?.avg_batch_size != null ? String(inferenceData.avg_batch_size) : "—"}
          sub={inferenceData?.batches_processed != null ? `${fmtInt(inferenceData.batches_processed)} batches` : undefined}
          accent="violet" loading={inferenceQ.isLoading && !inferenceData} />
      </div>

      {/* ── Queue + Cache side by side ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

        {/* Queue */}
        <Panel title="Queue Status" sub="Batch queues + job store snapshot"
          right={<LiveIndicator ok={!queuesQ.isError} />}>
          {queuesQ.isLoading && !queuesData ? (
            <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} className="h-8 rounded-lg" />)}</div>
          ) : queuesQ.isError ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-300">Service unreachable</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: "Active jobs", value: String(queuesData?.active_jobs ?? 0), accent: "cyan" as Accent },
                  { label: "In store",    value: String(queuesData?.jobs_in_store ?? 0), accent: "zinc" as Accent },
                  { label: "Queues",      value: String(sortedQueues.length), accent: "violet" as Accent },
                ].map(k => (
                  <div key={k.label} className={cn("rounded-xl border bg-zinc-950/40 px-3 py-3 text-center", ACCENT[k.accent].border)}>
                    <div className="text-[10px] uppercase tracking-widest text-zinc-600">{k.label}</div>
                    <div className={cn("mt-1 text-xl font-bold tabular-nums", ACCENT[k.accent].text)}>{k.value}</div>
                  </div>
                ))}
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Queue depths</span>
                  {sortedQueues.length > 0 && sortedQueues.every(([, v]) => v === 0) && (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-500">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      All clear
                    </span>
                  )}
                </div>
                {sortedQueues.length === 0 ? (
                  <div className="flex items-center gap-2 rounded-xl border border-zinc-800/60 bg-zinc-900/40 px-3 py-3">
                    <span className="text-xs text-zinc-600">No queue data available</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {sortedQueues.map(([k, v]) => <QueueBar key={k} name={k} depth={v} max={maxDepth} />)}
                  </div>
                )}
              </div>
            </div>
          )}
        </Panel>

        {/* Cache */}
        <Panel title="Cache Stats" sub="Hit rate + counts"
          right={<LiveIndicator ok={!inferenceQ.isError} />}>
          {inferenceQ.isLoading && !inferenceData ? (
            <div className="space-y-3">
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-8 rounded-lg" />
              <Skeleton className="h-8 rounded-lg" />
            </div>
          ) : inferenceQ.isError ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-300">Service unreachable</div>
          ) : cacheIsEmpty ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-zinc-800/60 bg-zinc-900/60">
                <Database className="h-7 w-7 text-zinc-700" strokeWidth={1.5} />
              </div>
              <div className="text-sm font-medium text-zinc-500">No cache data yet</div>
              <div className="text-xs text-zinc-700">Stats appear once requests are made</div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-5">
                <div className="relative h-28 w-28 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" innerRadius={34} outerRadius={52}
                        paddingAngle={3} startAngle={90} endAngle={-270} stroke="none" isAnimationActive={false}>
                        <Cell fill="#34d399" />
                        <Cell fill="#27272a" />
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <div className="text-xl font-bold text-emerald-400">{(cacheRate ?? 0).toFixed(0)}%</div>
                    <div className="text-[9px] text-zinc-600">hit rate</div>
                  </div>
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      <span className="text-xs text-zinc-400">Hits</span>
                    </div>
                    <span className="text-sm font-bold text-emerald-400 tabular-nums">{fmtInt(cacheHits ?? null)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2.5">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-red-400" />
                      <span className="text-xs text-zinc-400">Misses</span>
                    </div>
                    <span className="text-sm font-bold text-red-400 tabular-nums">{fmtInt(cacheMisses ?? null)}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-zinc-800">
                    <div className="h-full rounded-full bg-emerald-400 transition-all duration-700"
                      style={{ width: `${Math.max(0, cacheRate ?? 0)}%` }} />
                  </div>
                </div>
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* ── Requests by endpoint ─────────────────────────────────────────────── */}
      <Panel
        title="Requests by endpoint"
        sub="All-time totals from /stats"
        right={
          <div className="flex items-center gap-3">
            {statsQ.dataUpdatedAt && (
              <span className="text-[11px] text-zinc-600">
                Updated {format(new Date(statsQ.dataUpdatedAt), "HH:mm:ss")}
              </span>
            )}
            <LiveIndicator ok={!statsQ.isError} />
          </div>
        }
      >
        {statsQ.isLoading && !stats ? (
          <Skeleton className="h-[280px] w-full rounded-xl" />
        ) : statsQ.isError ? (
          <div className="flex h-[280px] items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/5 text-sm text-amber-300">
            Stats endpoint unavailable
          </div>
        ) : byEndpoint.length === 0 ? (
          <div className="flex h-[280px] flex-col items-center justify-center gap-3 text-center">
            <BarChart3 className="h-10 w-10 text-zinc-800" strokeWidth={1} />
            <div className="text-sm text-zinc-600">No endpoint data yet</div>
            <div className="text-xs text-zinc-700">Data appears once requests are made</div>
          </div>
        ) : (
          <EndpointBarChart data={byEndpoint} height={Math.max(280, byEndpoint.length * 36)} />
        )}
      </Panel>

      {/* ── Quick navigation ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { href: "/monitoring", label: "Deep-dive Monitoring", sub: "GPU charts · latency trends · queue history", icon: Activity, accent: "cyan" as Accent },
          { href: "/history",    label: "Request History",      sub: "All API requests · filter · export",          icon: TrendingUp, accent: "violet" as Accent },
          { href: "/usage",      label: "Usage & Billing",      sub: "Per-org token usage · cache · latency",       icon: BarChart3, accent: "emerald" as Accent },
        ].map(item => {
          const Icon = item.icon;
          const a = ACCENT[item.accent];
          return (
            <Link key={item.href} href={item.href}
              className={cn(
                "group relative overflow-hidden rounded-2xl border bg-zinc-900/60 p-4 backdrop-blur-sm transition-all hover:bg-zinc-900/90",
                a.border
              )}>
              <div className="absolute inset-x-0 top-0 h-px opacity-50"
                style={{ background: `linear-gradient(90deg,transparent,${a.top}60,transparent)` }} />
              <div className="flex items-center justify-between">
                <div>
                  <div className={cn("text-sm font-semibold", a.text)}>{item.label}</div>
                  <div className="mt-0.5 text-xs text-zinc-600">{item.sub}</div>
                </div>
                <div className="flex items-center gap-1.5">
                  <Icon className={cn("h-5 w-5", a.icon)} strokeWidth={1.5} />
                  <ExternalLink className="h-3.5 w-3.5 text-zinc-700 transition-colors group-hover:text-zinc-400" strokeWidth={1.5} />
                </div>
              </div>
            </Link>
          );
        })}
      </div>

    </div>
  );
}
