"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Database, Layers, Zap } from "lucide-react";
import { fetchMetricsOverview } from "@/lib/dashboardApi";

type TsPoint = {
  i: number;
  time: string;
  gpu: number;
  vram: number;
  activeJobs: number;
};

const CHART_COLORS = {
  gpu: "#22d3ee",
  vram: "#a78bfa",
  jobs: "#f472b6",
  bar: "#3f3f46",
  barHighlight: "#22d3ee",
};

function Panel({
  title,
  subtitle,
  children,
  icon: Icon,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/40 shadow-panel backdrop-blur-sm">
      <div className="border-b border-zinc-800/60 px-4 py-3">
        <div className="flex items-center gap-2">
          {Icon && (
            <Icon className="h-4 w-4 text-console-accent" strokeWidth={1.75} />
          )}
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
            {subtitle && (
              <p className="text-[11px] text-zinc-500">{subtitle}</p>
            )}
          </div>
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

const tooltipProps = {
  contentStyle: {
    backgroundColor: "rgba(24, 24, 27, 0.96)",
    border: "1px solid rgb(63 63 70)",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#e4e4e7",
  },
  labelStyle: { color: "#a1a1aa" },
};

export function MonitoringClient() {
  const [ts, setTs] = useState<TsPoint[]>([]);

  const { data, isLoading, isError, error, dataUpdatedAt, isFetching } = useQuery(
    {
      queryKey: ["metrics-overview"],
      queryFn: fetchMetricsOverview,
      refetchInterval: 4000,
    }
  );

  useEffect(() => {
    if (!data) return;
    setTs((prev) => {
      const row: TsPoint = {
        i: prev.length ? prev[prev.length - 1].i + 1 : 0,
        time: new Date().toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        gpu: data.gpu.available ? data.gpu.gpu_util_percent ?? 0 : 0,
        vram: data.gpu.available ? data.gpu.memory_used_percent ?? 0 : 0,
        activeJobs: data.queues.active_jobs,
      };
      return [...prev, row].slice(-100);
    });
  }, [data, dataUpdatedAt]);

  const endpointBars = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.inference.requests_by_endpoint)
      .map(([name, value]) => ({ name, value: Number(value) }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 14);
  }, [data]);

  const queueBars = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.queues.queue_depths).map(([name, value]) => ({
      name,
      value: Number(value),
    }));
  }, [data]);

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/30">
        <div className="flex items-center gap-3 text-sm text-zinc-500">
          <span className="h-2 w-2 animate-pulse rounded-full bg-console-accent" />
          Loading metrics…
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-red-900/60 bg-red-950/25 p-5 text-sm text-red-200 shadow-panel">
        {error instanceof Error ? error.message : "Failed to load metrics"}
      </div>
    );
  }

  if (!data) return null;

  const g = data.gpu;
  const inf = data.inference;
  const q = data.queues;
  const maxEndpoint = Math.max(1, ...endpointBars.map((b) => b.value));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span
            className={`inline-flex h-2 w-2 rounded-full ${
              isFetching ? "animate-pulse bg-console-accent" : "bg-emerald-500"
            }`}
          />
          {dataUpdatedAt
            ? `Updated ${new Date(dataUpdatedAt).toLocaleTimeString()} · 4s refresh`
            : "Live"}
        </div>
        {!g.available && (
          <span className="rounded-full border border-amber-900/50 bg-amber-950/30 px-3 py-1 text-[11px] text-amber-200/90">
            GPU charts need NVML (NVIDIA driver + nvidia-ml-py on API host)
          </span>
        )}
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Model"
          value={data.model_loaded ? "Ready" : "Not loaded"}
          sub={data.cuda_memory_gb != null ? `${data.cuda_memory_gb} GB CUDA` : "CPU / N/A"}
          ok={data.model_loaded}
        />
        <Stat
          label="Total requests"
          value={String(inf.total_requests)}
          sub="All-time counter"
        />
        <Stat
          label="Cache hit rate"
          value={`${inf.cache_hit_rate_percent.toFixed(1)}%`}
          sub="From server stats"
        />
        <Stat
          label="Active jobs"
          value={String(q.active_jobs)}
          sub={`${q.jobs_in_store} in job store`}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="GPU load (live)"
          subtitle="Util % and VRAM % — sampled each poll"
          icon={Zap}
        >
          {ts.length < 2 ? (
            <p className="py-8 text-center text-sm text-zinc-500">
              Collecting samples… Leave this page open for a few seconds.
            </p>
          ) : (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ts} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gpuFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART_COLORS.gpu} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={CHART_COLORS.gpu} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="vramFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART_COLORS.vram} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={CHART_COLORS.vram} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="time" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip {...tooltipProps} />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                  <Area type="monotone" dataKey="gpu" name="GPU %" stroke={CHART_COLORS.gpu} strokeWidth={2} fill="url(#gpuFill)" dot={false} isAnimationActive={false} />
                  <Area type="monotone" dataKey="vram" name="VRAM %" stroke={CHART_COLORS.vram} strokeWidth={2} fill="url(#vramFill)" dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel
          title="Active jobs"
          subtitle="Concurrent generation workload"
          icon={Activity}
        >
          {ts.length < 2 ? (
            <p className="py-8 text-center text-sm text-zinc-500">
              Collecting samples…
            </p>
          ) : (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ts} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="jobsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={CHART_COLORS.jobs} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={CHART_COLORS.jobs} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="time" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip {...tooltipProps} />
                  <Area type="monotone" dataKey="activeJobs" name="Active jobs" stroke={CHART_COLORS.jobs} strokeWidth={2} fill="url(#jobsFill)" dot={false} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Requests by endpoint" subtitle="Generation & traffic mix" icon={Layers}>
          {endpointBars.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">No endpoint data yet</p>
          ) : (
            <div className="h-[280px] w-full max-w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart layout="vertical" data={endpointBars} margin={{ left: 8, right: 16 }} barCategoryGap={6}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, maxEndpoint]} />
                  <YAxis type="category" dataKey="name" width={118} tick={{ fill: "#a1a1aa", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipProps} />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={22}>
                    {endpointBars.map((entry, i) => (
                      <Cell key={entry.name} fill={i < 3 ? CHART_COLORS.barHighlight : CHART_COLORS.bar} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Batch queues" subtitle="Depth per queue" icon={Database}>
          {queueBars.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">No queues</p>
          ) : (
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={queueBars} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "#71717a", fontSize: 10 }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip {...tooltipProps} />
                  <Bar dataKey="value" fill={CHART_COLORS.gpu} radius={[6, 6, 0, 0]} maxBarSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      </div>

      <Panel title="GPU details (NVML snapshot)" subtitle="Current reading from the API host">
        {!g.available ? (
          <p className="text-sm text-zinc-500">{g.error ?? "NVML not available."}</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <MiniMetric label="VRAM" value={`${g.memory_used_mb?.toFixed(0)} / ${g.memory_total_mb?.toFixed(0)} MB`} />
            <MiniMetric label="VRAM %" value={`${g.memory_used_percent?.toFixed(1)}%`} />
            <MiniMetric label="GPU util" value={`${g.gpu_util_percent}%`} />
            <MiniMetric label="Temperature" value={`${g.temperature_c}°C`} />
            {g.power_watts != null && (
              <MiniMetric label="Power" value={`${g.power_watts} W`} />
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  ok,
}: {
  label: string;
  value: string;
  sub?: string;
  ok?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 shadow-sm ${
        ok === undefined
          ? "border-zinc-800/80 bg-zinc-900/50"
          : ok
            ? "border-emerald-900/40 bg-emerald-950/15"
            : "border-amber-900/40 bg-amber-950/15"
      }`}
    >
      <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tracking-tight text-zinc-50">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-zinc-500">{sub}</div>}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</div>
      <div className="text-sm font-medium text-zinc-200">{value}</div>
    </div>
  );
}
