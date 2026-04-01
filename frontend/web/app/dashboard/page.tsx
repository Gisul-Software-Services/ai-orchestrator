"use client";

import {
  useHealthQuery,
  useMetricsInferenceQuery,
  useMetricsOverviewQuery,
  useMetricsQueuesQuery,
  useStatsQuery,
} from "@/hooks/useMetrics";
import { GpuPanel } from "@/components/dashboard/GpuPanel";
import { QueuePanel } from "@/components/dashboard/QueuePanel";
import { CachePanel } from "@/components/dashboard/CachePanel";
import { InferencePanel } from "@/components/dashboard/InferencePanel";
import { EndpointBarChart } from "@/components/dashboard/EndpointBarChart";
import type { MetricsOverview, StatsResponse } from "@/types/api";
import { Skeleton } from "@/components/ui/skeleton";

function sortEndpointCounts(m: Record<string, number> | undefined | null) {
  return Object.entries(m ?? {})
    .map(([endpoint, value]) => ({ endpoint, value }))
    .sort((a, b) => b.value - a.value);
}

export default function DashboardPage() {
  const healthQ = useHealthQuery();
  const overviewQ = useMetricsOverviewQuery();
  const queuesQ = useMetricsQueuesQuery();
  const inferenceQ = useMetricsInferenceQuery();
  const statsQ = useStatsQuery();

  const unreachable =
    healthQ.isError || overviewQ.isError || queuesQ.isError || inferenceQ.isError;

  const overview = overviewQ.data as MetricsOverview | undefined;
  const stats = statsQ.data as StatsResponse | undefined;

  const lastOkAt = Math.max(
    healthQ.isSuccess ? healthQ.dataUpdatedAt : 0,
    overviewQ.isSuccess ? overviewQ.dataUpdatedAt : 0,
    queuesQ.isSuccess ? queuesQ.dataUpdatedAt : 0,
    inferenceQ.isSuccess ? inferenceQ.dataUpdatedAt : 0,
    statsQ.isSuccess ? statsQ.dataUpdatedAt : 0
  );
  const lastOk = lastOkAt > 0 ? lastOkAt : null;

  const modelLoaded = healthQ.data?.model_loaded ?? overview?.model_loaded ?? false;

  const queuesPayload = (queuesQ.data as any) ?? null;
  const cacheHits = (inferenceQ.data as any)?.cache_hits as number | undefined;
  const cacheMisses = (inferenceQ.data as any)?.cache_misses as number | undefined;
  const cacheHitRate = (inferenceQ.data as any)?.cache_hit_rate_percent as
    | number
    | undefined;

  const totalGenSeconds = (inferenceQ.data as any)?.total_generation_time_seconds as
    | number
    | undefined;
  const totalRequests = (inferenceQ.data as any)?.total_requests as number | undefined;
  const errors = (inferenceQ.data as any)?.errors as number | undefined;

  const avgLatencySeconds =
    typeof totalGenSeconds === "number" && typeof totalRequests === "number" && totalRequests > 0
      ? totalGenSeconds / totalRequests
      : null;
  const errorRatePercent =
    typeof errors === "number" && typeof totalRequests === "number" && totalRequests > 0
      ? (100 * errors) / totalRequests
      : null;

  const topEndpoints = sortEndpointCounts(overview?.inference?.requests_by_endpoint);
  const byEndpointStats = sortEndpointCounts(stats?.requests_by_endpoint);

  return (
    <div className="space-y-6">
      {!modelLoaded && !unreachable ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          <div className="font-medium">Model is not loaded yet</div>
          <div className="mt-1 text-xs text-amber-200/80">
            The service is reachable, but `model_loaded` is false. Generation
            endpoints may be unavailable until the model finishes loading.
          </div>
        </div>
      ) : null}

      <GpuPanel
        health={healthQ.data ?? null}
        overview={overview ?? null}
        loading={healthQ.isLoading || overviewQ.isLoading}
        unreachable={healthQ.isError || overviewQ.isError}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <QueuePanel
          loading={queuesQ.isLoading}
          error={queuesQ.isError}
          lastOkAt={lastOk}
          queues={queuesQ.isSuccess ? queuesPayload : null}
        />

        <CachePanel
          loading={inferenceQ.isLoading}
          error={inferenceQ.isError}
          lastOkAt={lastOk}
          cacheHitRatePercent={typeof cacheHitRate === "number" ? cacheHitRate : null}
          hits={typeof cacheHits === "number" ? cacheHits : null}
          misses={typeof cacheMisses === "number" ? cacheMisses : null}
        />

        <InferencePanel
          loading={inferenceQ.isLoading}
          error={inferenceQ.isError}
          lastOkAt={lastOk}
          avgLatencySeconds={avgLatencySeconds}
          totalRequests={typeof totalRequests === "number" ? totalRequests : null}
          errorRatePercent={errorRatePercent}
          requestsByEndpoint={overview?.inference?.requests_by_endpoint ?? null}
        />
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
        <div className="mb-2">
          <div className="text-sm font-semibold text-zinc-50">
            Requests by endpoint
          </div>
          <div className="text-xs text-zinc-400">
            From `/stats` (sorted descending)
          </div>
        </div>
        {statsQ.isLoading ? (
          <Skeleton className="h-[260px] w-full" />
        ) : statsQ.isError ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
            <div className="font-medium">Could not reach model-service</div>
            <div className="mt-1 text-xs text-amber-200/80">
              Last successful fetch:{" "}
              {lastOk ? new Date(lastOk).toLocaleString() : "never"}
            </div>
          </div>
        ) : (
          <EndpointBarChart data={byEndpointStats} height={320} />
        )}
      </div>
    </div>
  );
}

