"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { buildCsv, downloadCsv } from "@/components/usage/csv";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ChevronUp, ChevronDown } from "lucide-react";

export type OrgUsageRow = {
  org_id: string;
  org_name?: string | null;
  total_tokens?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  call_count?: number | null;
  cache_hit_rate_percent?: number | null;
  cache_hits?: number | null;
  avg_latency_ms?: number | null;
  errors?: number | null;
  last_active?: string | null;
};

function fmtNum(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return <span className="text-zinc-600">—</span>;
  return <span className="tabular-nums">{n.toLocaleString()}</span>;
}

function fmtPct(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return <span className="text-zinc-600">—</span>;
  const color = n >= 70 ? "text-emerald-400" : n >= 40 ? "text-amber-400" : "text-red-400";
  return <span className={cn("tabular-nums font-medium", color)}>{n.toFixed(1)}%</span>;
}

function fmtMs(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return <span className="text-zinc-600">—</span>;
  const ms = Math.round(Number(n));
  const color = ms < 500 ? "text-emerald-400" : ms < 2000 ? "text-amber-400" : "text-red-400";
  return <span className={cn("tabular-nums font-medium", color)}>{ms} ms</span>;
}

function fmtErrors(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return <span className="text-zinc-600">—</span>;
  if (n === 0) return <span className="text-zinc-500">0</span>;
  return <span className="tabular-nums font-medium text-red-400">{n.toLocaleString()}</span>;
}

export function OrgsTable({
  rows,
  period,
  loading,
}: {
  rows: OrgUsageRow[];
  period: string;
  loading: boolean;
}) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "total_tokens", desc: true },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<OrgUsageRow>[]>(
    () => [
      {
        header: "Org ID",
        accessorKey: "org_id",
        cell: (ctx) => (
          <span className="font-mono text-xs text-zinc-200">{String(ctx.getValue())}</span>
        ),
      },
      {
        header: "Org Name",
        accessorKey: "org_name",
        cell: (ctx) => (
          <span className="text-zinc-300">
            {ctx.getValue() ? String(ctx.getValue()) : <span className="text-zinc-600">—</span>}
          </span>
        ),
      },
      {
        header: "Total Tokens",
        accessorKey: "total_tokens",
        cell: (ctx) => fmtNum(ctx.getValue() as number | null),
      },
      {
        header: "Prompt",
        accessorKey: "prompt_tokens",
        cell: (ctx) => fmtNum(ctx.getValue() as number | null),
      },
      {
        header: "Completion",
        accessorKey: "completion_tokens",
        cell: (ctx) => fmtNum(ctx.getValue() as number | null),
      },
      {
        header: "API Calls",
        accessorKey: "call_count",
        cell: (ctx) => fmtNum(ctx.getValue() as number | null),
      },
      {
        header: "Cache Hit %",
        accessorKey: "cache_hit_rate_percent",
        cell: (ctx) => fmtPct(ctx.getValue() as number | null),
      },
      {
        header: "Avg Latency",
        accessorKey: "avg_latency_ms",
        cell: (ctx) => fmtMs(ctx.getValue() as number | null),
      },
      {
        header: "Errors",
        accessorKey: "errors",
        cell: (ctx) => fmtErrors(ctx.getValue() as number | null),
      },
      {
        header: "Last Active",
        accessorKey: "last_active",
        cell: (ctx) => (
          <span className="font-mono text-xs text-zinc-400">
            {ctx.getValue() ? String(ctx.getValue()) : <span className="text-zinc-600">—</span>}
          </span>
        ),
      },
      {
        header: "Actions",
        id: "actions",
        enableSorting: false,
        cell: (ctx) => {
          const orgId = ctx.row.original.org_id;
          const qs = new URLSearchParams({ period }).toString();
          return (
            <Link
              href={`/usage/${encodeURIComponent(orgId)}?${qs}`}
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-700/60 bg-zinc-900 px-2.5 py-1 text-xs font-medium text-zinc-300 transition-colors hover:border-cyan-500/40 hover:text-console-accent"
            >
              Details →
            </Link>
          );
        },
      },
    ],
    [period]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, _columnId, filterValue) => {
      const q = String(filterValue ?? "").toLowerCase().trim();
      if (!q) return true;
      const id = String(row.original.org_id ?? "").toLowerCase();
      const name = String(row.original.org_name ?? "").toLowerCase();
      return id.includes(q) || name.includes(q);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 20 } },
  });

  const exportAll = () => {
    const headers = [
      "Org ID", "Org Name", "Total Tokens", "Prompt Tokens", "Completion Tokens",
      "API Calls", "Cache Hit %", "Avg Latency ms", "Errors", "Last Active",
    ];
    const csvRows = rows.map((r) => ({
      "Org ID": r.org_id,
      "Org Name": r.org_name ?? "",
      "Total Tokens": r.total_tokens ?? "",
      "Prompt Tokens": r.prompt_tokens ?? "",
      "Completion Tokens": r.completion_tokens ?? "",
      "API Calls": r.call_count ?? "",
      "Cache Hit %": r.cache_hit_rate_percent != null ? r.cache_hit_rate_percent.toFixed(2) : "",
      "Avg Latency ms": r.avg_latency_ms != null ? Math.round(r.avg_latency_ms) : "",
      "Errors": r.errors ?? "",
      "Last Active": r.last_active ?? "",
    }));
    downloadCsv(`gisul-usage-${period}.csv`, buildCsv(headers, csvRows));
  };

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 backdrop-blur-sm">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 border-b border-zinc-800/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <input
          className="h-9 w-full rounded-lg border border-zinc-700/60 bg-zinc-950/60 px-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-cyan-500/40 sm:w-[280px]"
          placeholder="Search org ID or name…"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
        <Button
          variant="outline"
          className="border-zinc-700/60 hover:border-zinc-600"
          onClick={exportAll}
          disabled={rows.length === 0}
        >
          Export CSV
        </Button>
      </div>

      {loading ? (
        <div className="p-4 space-y-2">
          <Skeleton className="h-10 w-full rounded-lg" />
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <>
          <div className="overflow-auto">
            <table className="min-w-[1200px] w-full text-left text-sm">
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id} className="border-b border-zinc-800/60">
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        className={cn(
                          "px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500",
                          h.column.getCanSort() && "cursor-pointer select-none hover:text-zinc-300"
                        )}
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {h.column.getCanSort() && (
                            <span className="text-zinc-700">
                              {h.column.getIsSorted() === "asc" ? (
                                <ChevronUp className="h-3 w-3 text-console-accent" />
                              ) : h.column.getIsSorted() === "desc" ? (
                                <ChevronDown className="h-3 w-3 text-console-accent" />
                              ) : (
                                <ArrowUpDown className="h-3 w-3" />
                              )}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td
                      className="px-4 py-10 text-center text-sm text-zinc-600"
                      colSpan={columns.length}
                    >
                      No usage data for this period.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-zinc-800/40 transition-colors hover:bg-zinc-800/30"
                    >
                      {r.getVisibleCells().map((c) => (
                        <td key={c.id} className="px-4 py-2.5">
                          {flexRender(c.column.columnDef.cell, c.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between gap-3 border-t border-zinc-800/60 px-4 py-3 text-xs text-zinc-500">
            <div>
              Showing{" "}
              <span className="font-medium text-zinc-300">
                {table.getRowModel().rows.length}
              </span>{" "}
              of{" "}
              <span className="font-medium text-zinc-300">
                {table.getFilteredRowModel().rows.length}
              </span>{" "}
              orgs
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="border-zinc-700/60 h-7 px-3 text-xs"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                Prev
              </Button>
              <span className="text-zinc-500">
                {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
              </span>
              <Button
                variant="outline"
                className="border-zinc-700/60 h-7 px-3 text-xs"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
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
