"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";
import { EndpointBarChart } from "./EndpointBarChart";

export function InferencePanel({
  loading,
  error,
  lastOkAt,
  avgLatencySeconds,
  totalRequests,
  errorRatePercent,
  requestsByEndpoint,
}: {
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  avgLatencySeconds: number | null;
  totalRequests: number | null;
  errorRatePercent: number | null;
  requestsByEndpoint: Record<string, number> | null;
}) {
  const endpointData = Object.entries(requestsByEndpoint ?? {})
    .map(([endpoint, value]) => ({ endpoint, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-50">
            Inference stats
          </div>
          <div className="text-xs text-zinc-400">
            Latency + errors + endpoint mix
          </div>
        </div>
        <LiveIndicator ok={!error} label={!error ? "Live" : "Degraded"} />
      </div>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-56" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          <div className="font-medium">Could not reach model-service</div>
          <div className="mt-1 text-xs text-amber-200/80">
            Last successful fetch:{" "}
            {lastOkAt ? new Date(lastOkAt).toLocaleString() : "never"}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Avg latency" value={fmtSeconds(avgLatencySeconds)} />
            <Stat label="Total requests" value={fmtInt(totalRequests)} />
            <Stat label="Error rate" value={fmtPercent(errorRatePercent)} />
          </div>
          <div>
            <div className="mb-2 text-xs font-medium text-zinc-400">
              Top endpoints
            </div>
            <EndpointBarChart data={endpointData} height={190} />
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-zinc-900/40 p-3">
      <div className="text-xs text-zinc-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-zinc-50">{value}</div>
    </div>
  );
}

function fmtInt(n: number | null) {
  return typeof n === "number" ? n.toLocaleString() : "—";
}

function fmtPercent(n: number | null) {
  return typeof n === "number" ? `${n.toFixed(2)}%` : "—";
}

function fmtSeconds(n: number | null) {
  return typeof n === "number" ? `${n.toFixed(2)}s` : "—";
}

