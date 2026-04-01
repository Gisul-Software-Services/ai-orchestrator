"use client";

import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { buildCsv, downloadCsv } from "@/components/usage/csv";
import { Skeleton } from "@/components/ui/skeleton";

export type UsageLogRow = {
  created_at?: string;
  route?: string;
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  latency_ms?: number;
  cache_hit?: boolean;
  status?: string;
  job_id?: string;
};

function fmtTime(ts?: string) {
  if (!ts) return "—";
  return String(ts).replace("T", " ").slice(0, 19);
}

function badgeClass(kind: "ok" | "bad" | "neutral") {
  if (kind === "ok") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
  if (kind === "bad") return "border-red-500/30 bg-red-500/10 text-red-200";
  return "border-white/10 bg-white/5 text-zinc-300";
}

function truncate(s: string, n: number) {
  if (s.length <= n) return s;
  return `${s.slice(0, n)}…`;
}

export function LogsTable({
  orgId,
  period,
  rows,
  loading,
  error,
  page,
  pageSize,
  onPageChange,
  routeFilter,
  statusFilter,
  onRouteFilterChange,
  onStatusFilterChange,
  allRoutes,
}: {
  orgId: string;
  period: string;
  rows: UsageLogRow[];
  loading: boolean;
  error: string | null;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  routeFilter: string;
  statusFilter: "all" | "success" | "error";
  onRouteFilterChange: (v: string) => void;
  onStatusFilterChange: (v: "all" | "success" | "error") => void;
  allRoutes: string[];
}) {
  const exportPage = () => {
    const headers = [
      "Timestamp",
      "Route",
      "Total Tokens",
      "Prompt Tokens",
      "Completion Tokens",
      "Latency ms",
      "Cache Hit",
      "Status",
      "Job ID",
    ];
    const csvRows = rows.map((r) => ({
      Timestamp: fmtTime(r.created_at),
      Route: r.route ?? "",
      "Total Tokens": r.total_tokens ?? "",
      "Prompt Tokens": r.prompt_tokens ?? "",
      "Completion Tokens": r.completion_tokens ?? "",
      "Latency ms": r.latency_ms ?? "",
      "Cache Hit": r.cache_hit ? "yes" : "no",
      Status: r.status ?? "",
      "Job ID": r.job_id ?? "",
    }));
    downloadCsv(`gisul-logs-${orgId}-${period}-page${page}.csv`, buildCsv(headers, csvRows));
  };

  const routeOptions = useMemo(() => ["", ...allRoutes], [allRoutes]);

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40">
      <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Route</span>
            <select
              className="h-9 rounded-md border border-white/10 bg-zinc-950/40 px-3 text-sm text-zinc-200 outline-none focus:border-cyan-500/40"
              value={routeFilter}
              onChange={(e) => onRouteFilterChange(e.target.value)}
            >
              {routeOptions.map((r) => (
                <option key={r || "__all"} value={r}>
                  {r ? r : "All"}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Status</span>
            <select
              className="h-9 rounded-md border border-white/10 bg-zinc-950/40 px-3 text-sm text-zinc-200 outline-none focus:border-cyan-500/40"
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value as any)}
            >
              <option value="all">All</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="border-white/10"
            onClick={exportPage}
            disabled={rows.length === 0}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="p-4">
          <Skeleton className="h-10 w-full" />
          <div className="mt-3 space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="p-4 text-sm text-amber-200">{error}</div>
      ) : (
        <>
          <div className="overflow-auto">
            <table className="min-w-[1150px] w-full text-left text-sm">
              <thead className="text-xs text-zinc-500">
                <tr className="border-b border-white/10">
                  <th className="px-4 py-2">Timestamp</th>
                  <th className="px-4 py-2">Route</th>
                  <th className="px-4 py-2">Total Tokens</th>
                  <th className="px-4 py-2">Prompt / Completion</th>
                  <th className="px-4 py-2">Latency ms</th>
                  <th className="px-4 py-2">Cache Hit</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Job ID</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {rows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-10 text-center text-zinc-500" colSpan={8}>
                      No logs found for this filter.
                    </td>
                  </tr>
                ) : (
                  rows.map((r, idx) => {
                    const status = (r.status ?? "").toLowerCase();
                    const ok = status === "success";
                    const bad = status === "error";
                    const jobId = r.job_id ?? "";
                    return (
                      <tr key={`${r.created_at ?? "t"}-${idx}`} className="border-b border-white/5 hover:bg-white/5">
                        <td className="px-4 py-2 font-mono text-xs text-zinc-400">{fmtTime(r.created_at)}</td>
                        <td className="px-4 py-2 font-mono text-xs text-zinc-300">{r.route ?? "—"}</td>
                        <td className="px-4 py-2 tabular-nums">{r.total_tokens ?? "—"}</td>
                        <td className="px-4 py-2 tabular-nums">
                          {(r.prompt_tokens ?? 0).toLocaleString()} / {(r.completion_tokens ?? 0).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 tabular-nums">{r.latency_ms != null ? Math.round(r.latency_ms) : "—"}</td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${badgeClass(r.cache_hit ? "ok" : "neutral")}`}>
                            {r.cache_hit ? "yes" : "no"}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${badgeClass(ok ? "ok" : bad ? "bad" : "neutral")}`}>
                            {r.status ?? "—"}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          {jobId ? (
                            <button
                              type="button"
                              className="font-mono text-xs text-cyan-300 hover:underline"
                              title={jobId}
                              onClick={() => navigator.clipboard.writeText(jobId)}
                            >
                              {truncate(jobId, 10)}
                            </button>
                          ) : (
                            <span className="text-zinc-500">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between gap-3 px-4 py-3 text-xs text-zinc-500">
            <div>
              Page{" "}
              <span className="font-medium text-zinc-300">{page}</span> (page size{" "}
              <span className="font-medium text-zinc-300">{pageSize}</span>)
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="border-white/10"
                onClick={() => onPageChange(Math.max(1, page - 1))}
                disabled={page <= 1}
              >
                Prev
              </Button>
              <Button
                variant="outline"
                className="border-white/10"
                onClick={() => onPageChange(page + 1)}
                disabled={rows.length < pageSize}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

