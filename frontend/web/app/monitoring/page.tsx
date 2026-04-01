"use client";

import { format } from "date-fns";
import { Pie, PieChart, ResponsiveContainer, Cell } from "recharts";
import { LiveIndicator } from "@/components/dashboard/LiveIndicator";
import { CacheDonut } from "@/components/monitoring/CacheDonut";
import { GpuChart } from "@/components/monitoring/GpuChart";
import { InferenceCharts } from "@/components/monitoring/InferenceCharts";
import { QueueChart } from "@/components/monitoring/QueueChart";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetricsHistory } from "@/hooks/useMetricsHistory";
import { useStatsQuery } from "@/hooks/useMetrics";

function asBool(v: unknown): boolean {
  return v === true;
}

function asNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) {
    return Number(v);
  }
  return null;
}

function asInt(v: unknown): number {
  const n = asNumber(v);
  if (n === null) return 0;
  return Math.trunc(n);
}

function statusForDepth(n: number) {
  if (n <= 0) return "ok";
  if (n <= 5) return "warn";
  return "crit";
}

function statusDot(s: "ok" | "warn" | "crit") {
  if (s === "crit") return "bg-red-400";
  if (s === "warn") return "bg-amber-400";
  return "bg-emerald-400";
}

function fmtPct(v: number | null) {
  if (v === null || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)}%`;
}

export default function MonitoringPage() {
  const { gpuHistory, inferenceHistory, queueHistory, gpuQuery, inferenceQuery, queuesQuery } =
    useMetricsHistory();
  const statsQuery = useStatsQuery();

  const gpuAvailable = asBool((gpuQuery.data as any)?.available);
  const gpuError = (gpuQuery.data as any)?.error as string | null | undefined;

  const anyError =
    Boolean(gpuQuery.error) ||
    Boolean(inferenceQuery.error) ||
    Boolean(queuesQuery.error) ||
    Boolean(statsQuery.error);

  const lastUpdatedAt = Math.max(
    gpuQuery.dataUpdatedAt ?? 0,
    inferenceQuery.dataUpdatedAt ?? 0,
    queuesQuery.dataUpdatedAt ?? 0,
    statsQuery.dataUpdatedAt ?? 0
  );
  const stale = !lastUpdatedAt || Date.now() - lastUpdatedAt > 15_000 || anyError;

  const totalRequestsAllTime = statsQuery.data?.total_requests ?? null;
  const avgBatchSize = statsQuery.data?.avg_batch_size ?? null;

  const infTotalReq = asInt((inferenceQuery.data as any)?.total_requests);
  const infErrors = asInt((inferenceQuery.data as any)?.errors);
  const errorRate =
    infTotalReq > 0 ? Math.min(100, (100 * infErrors) / infTotalReq) : null;

  const cacheHitRateStats = statsQuery.data?.cache_hit_rate_percent ?? null;

  const overviewUnreachableBanner = anyError ? (
    <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      Model-service appears unreachable. Showing last known data where available.
    </div>
  ) : null;

  const queuesPayload = (queuesQuery.data ?? {}) as any;
  const queueDepths = (queuesPayload.queue_depths ?? {}) as Record<string, unknown>;
  const activeJobs = asInt(queuesPayload.active_jobs);

  const hasAnyGpuHistory = gpuHistory.length > 0;
  const hasAnyInferenceHistory = inferenceHistory.length > 0;
  const hasAnyQueueHistory = queueHistory.length > 0;

  const smallDonutData = [
    { name: "Hit", value: Math.max(0, cacheHitRateStats ?? 0) },
    { name: "Miss", value: Math.max(0, 100 - (cacheHitRateStats ?? 0)) },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-2xl font-semibold">Monitoring</div>
          <div className="mt-1 text-sm text-zinc-400">
            Live metrics — updates every 5 seconds
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-xs text-zinc-500">
            Last updated{" "}
            <span className="font-medium text-zinc-300">
              {lastUpdatedAt ? format(new Date(lastUpdatedAt), "HH:mm:ss") : "—"}
            </span>
          </div>
          <LiveIndicator ok={!stale} label={stale ? "Stale" : "Live"} />
        </div>
      </div>

      {overviewUnreachableBanner}

      {/* Section 1 — GPU & Hardware */}
      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-lg font-semibold text-zinc-100">GPU & Hardware</div>
            {!gpuAvailable && gpuQuery.isSuccess ? (
              <div className="mt-1 text-sm text-zinc-400">
                GPU metrics unavailable — pynvml not installed or no CUDA device detected
              </div>
            ) : null}
          </div>
        </div>

        {!hasAnyGpuHistory && gpuQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            <Skeleton className="h-[260px] rounded-xl" />
            <Skeleton className="h-[260px] rounded-xl" />
            <Skeleton className="h-[260px] rounded-xl" />
            <Skeleton className="h-[260px] rounded-xl" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            <GpuChart
              title="VRAM Usage"
              data={gpuHistory}
              metric="vram_percent"
              unit="%"
              yDomain={[0, 100]}
              warnAt={90}
              criticalAt={90}
              thresholds={[{ value: 90, color: "#ef4444", label: "90%" }]}
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
              yDomain={[0, 100]}
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
                unit="W"
                digits={0}
                unavailableMessage={!gpuAvailable ? gpuError ?? "Unavailable" : null}
              />
            ) : (
              <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
                <div className="text-sm text-zinc-200">Power Draw</div>
                <div className="mt-2 text-sm text-zinc-500">
                  Power data unavailable
                </div>
                <div className="mt-4">
                  <Skeleton className="h-[200px]" />
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Section 2 — Inference Metrics */}
      <section className="space-y-4">
        <div className="text-lg font-semibold text-zinc-100">Inference Metrics</div>

        {!hasAnyInferenceHistory && inferenceQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Skeleton className="h-[260px] rounded-xl" />
            <Skeleton className="h-[260px] rounded-xl" />
          </div>
        ) : (
          <InferenceCharts data={inferenceHistory as any} />
        )}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
            <div className="text-xs text-zinc-500">Total Requests (all time)</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">
              {totalRequestsAllTime ?? "—"}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
            <div className="text-xs text-zinc-500">Error Rate</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">
              {fmtPct(errorRate)}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
            <div className="text-xs text-zinc-500">Cache Hit Rate</div>
            <div className="mt-1 flex items-center justify-between gap-3">
              <div className="text-2xl font-semibold tabular-nums">
                {cacheHitRateStats !== null ? `${cacheHitRateStats.toFixed(2)}%` : "—"}
              </div>
              <div className="h-[52px] w-[52px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={smallDonutData}
                      dataKey="value"
                      innerRadius={16}
                      outerRadius={24}
                      paddingAngle={1}
                      isAnimationActive={false}
                    >
                      <Cell fill="#22c55e" />
                      <Cell fill="rgba(255,255,255,0.12)" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
            <div className="text-xs text-zinc-500">Avg Batch Size</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">
              {avgBatchSize ?? "—"}
            </div>
          </div>
        </div>
      </section>

      {/* Section 3 — Queue Status */}
      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <div className="text-lg font-semibold text-zinc-100">Queue Status</div>
          <div className="text-xs text-zinc-500">
            Active jobs:{" "}
            <span className="font-medium text-zinc-300">{activeJobs}</span>
          </div>
        </div>

        {!hasAnyQueueHistory && queuesQuery.isLoading ? (
          <Skeleton className="h-[290px] rounded-xl" />
        ) : (
          <QueueChart data={queueHistory as any} />
        )}

        <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950/40">
          <div className="border-b border-white/10 px-4 py-3 text-sm text-zinc-200">
            Current snapshot
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-zinc-500">
                <tr className="border-b border-white/10">
                  <th className="px-4 py-2">Queue Name</th>
                  <th className="px-4 py-2">Current Depth</th>
                  <th className="px-4 py-2">Active Jobs</th>
                  <th className="px-4 py-2">Status</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {Object.entries(queueDepths).map(([name, depth]) => {
                  const d = asInt(depth);
                  const s = statusForDepth(d);
                  return (
                    <tr key={name} className="border-b border-white/5">
                      <td className="px-4 py-2 font-medium">{name}</td>
                      <td className="px-4 py-2 tabular-nums">{d}</td>
                      <td className="px-4 py-2 text-zinc-400">—</td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`h-2.5 w-2.5 rounded-full ${statusDot(s)}`}
                          />
                          <span className="text-xs text-zinc-400">
                            {s === "ok" ? "Empty" : s === "warn" ? "Busy" : "Backlogged"}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {Object.keys(queueDepths).length === 0 ? (
                  <tr>
                    <td className="px-4 py-3 text-zinc-500" colSpan={4}>
                      No queues reported.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Section 4 — Cache Panel */}
      <section className="space-y-4">
        <div className="text-lg font-semibold text-zinc-100">Cache</div>
        <CacheDonut snapshot={(inferenceQuery.data ?? null) as any} />
      </section>
    </div>
  );
}
