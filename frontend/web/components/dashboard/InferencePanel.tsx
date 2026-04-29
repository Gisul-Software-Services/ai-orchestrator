"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { LiveIndicator } from "./LiveIndicator";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function InferencePanel({
  loading,
  error,
  lastOkAt,
  avgLatencyMs,
  totalRequests,
  errorRatePercent,
  requestsByEndpoint,
}: {
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  avgLatencyMs: number | null;
  totalRequests: number | null;
  errorRatePercent: number | null;
  requestsByEndpoint: Record<string, number> | null;
}) {
  const endpointData = Object.entries(requestsByEndpoint ?? {})
    .map(([endpoint, value]) => ({ endpoint: endpoint.replace("/api/v1/", ""), value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-zinc-100">Inference stats</div>
          <div className="text-xs text-zinc-500">Latency · requests · errors</div>
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
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">
          <div className="font-medium">Service unreachable</div>
          <div className="mt-1 text-xs text-amber-300/70">
            Last fetch: {lastOkAt ? new Date(lastOkAt).toLocaleString() : "never"}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* KPI row */}
          <div className="grid grid-cols-3 gap-2">
            <Kpi label="Avg latency" value={fmtMs(avgLatencyMs)} accent="cyan" />
            <Kpi label="Total reqs" value={fmtInt(totalRequests)} accent="violet" />
            <Kpi label="Error rate" value={fmtPct(errorRatePercent)} accent={
              errorRatePercent !== null && errorRatePercent > 5 ? "red" : "emerald"
            } />
          </div>

          {/* Endpoint bar chart */}
          {endpointData.length > 0 ? (
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                Top endpoints
              </div>
              <div className="h-[160px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={endpointData}
                    layout="vertical"
                    margin={{ top: 0, right: 8, bottom: 0, left: 0 }}
                    barCategoryGap={6}
                  >
                    <XAxis
                      type="number"
                      tick={{ fill: "#52525b", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="endpoint"
                      width={90}
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(9,9,11,0.95)",
                        border: "1px solid rgba(63,63,70,0.8)",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "#fafafa",
                      }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={14}>
                      {endpointData.map((_, i) => (
                        <Cell
                          key={i}
                          fill={i === 0 ? "#22d3ee" : i === 1 ? "#a78bfa" : "#3f3f46"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="flex h-[160px] items-center justify-center text-xs text-zinc-600">
              No endpoint data yet
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, accent }: { label: string; value: string; accent: string }) {
  const textColor =
    accent === "cyan" ? "text-console-accent"
    : accent === "violet" ? "text-console-violet"
    : accent === "red" ? "text-red-400"
    : accent === "emerald" ? "text-emerald-400"
    : "text-zinc-300";

  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-2.5 py-2">
      <div className="text-[10px] text-zinc-600">{label}</div>
      <div className={`mt-0.5 text-base font-bold tabular-nums ${textColor}`}>{value}</div>
    </div>
  );
}

function fmtInt(n: number | null) {
  return typeof n === "number" ? n.toLocaleString() : "—";
}

function fmtPct(n: number | null) {
  return typeof n === "number" ? `${n.toFixed(2)}%` : "—";
}

function fmtMs(n: number | null) {
  return typeof n === "number" ? `${n.toFixed(0)} ms` : "—";
}
