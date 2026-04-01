"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { LogFilters, type HistoryFilters } from "@/components/history/LogFilters";
import { RequestLogTable } from "@/components/history/RequestLogTable";
import { useRequestLogQuery } from "@/hooks/useHistory";

export default function HistoryPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<"timestamp" | "latency_ms">("timestamp");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [filters, setFilters] = useState<HistoryFilters>({
    endpoint: "",
    org_id: "",
    status: "all",
    start_date: "",
    end_date: "",
  });

  const query = useRequestLogQuery(
    {
      endpoint: filters.endpoint || undefined,
      org_id: filters.org_id || undefined,
      status: filters.status,
      start_date: filters.start_date || undefined,
      end_date: filters.end_date || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    },
    page,
    50,
    autoRefresh
  );

  const stats = useMemo(() => {
    const items = query.data?.items ?? [];
    const total = items.length;
    const errors = items.filter((x) => Number(x.status_code) >= 400).length;
    const avgLatency =
      total > 0
        ? Math.round(
            items.reduce((a, x) => a + Number(x.latency_ms ?? 0), 0) / total
          )
        : 0;
    const errorRate = total > 0 ? (100 * errors) / total : 0;
    return { total, errors, avgLatency, errorRate };
  }, [query.data?.items]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-2xl font-semibold">Request History</div>
          <div className="mt-1 text-sm text-zinc-400">
            All API requests — last 1000 entries
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-refresh (15s)</span>
          </label>
          <Button
            variant="outline"
            className="border-white/10"
            onClick={() => query.refetch()}
          >
            Refresh
          </Button>
        </div>
      </div>

      <LogFilters
        value={filters}
        onChange={(v) => {
          setFilters(v);
          setPage(1);
        }}
        onClear={() => {
          setFilters({
            endpoint: "",
            org_id: "",
            status: "all",
            start_date: "",
            end_date: "",
          });
          setPage(1);
        }}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Total requests shown</div>
          <div className="mt-1 text-2xl font-semibold">{stats.total}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Errors</div>
          <div className="mt-1 text-2xl font-semibold">
            {stats.errors} ({stats.errorRate.toFixed(2)}%)
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Avg latency</div>
          <div className="mt-1 text-2xl font-semibold">{stats.avgLatency} ms</div>
        </div>
      </div>

      {query.isError ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {query.error instanceof Error ? query.error.message : "Failed to load history"}
        </div>
      ) : (
        <RequestLogTable
          items={query.data?.items ?? []}
          total={query.data?.total ?? 0}
          page={page}
          pageSize={50}
          onPageChange={setPage}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSortChange={(s) => {
            setSortBy(s.sortBy);
            setSortOrder(s.sortOrder);
            setPage(1);
          }}
        />
      )}
    </div>
  );
}
