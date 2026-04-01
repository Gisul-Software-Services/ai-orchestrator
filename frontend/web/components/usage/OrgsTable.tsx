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
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

function fmtPct(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${n.toFixed(2)}%`;
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
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<OrgUsageRow>[]>(
    () => [
      {
        header: "Org ID",
        accessorKey: "org_id",
        cell: (ctx) => (
          <span className="font-mono text-zinc-200">{String(ctx.getValue())}</span>
        ),
      },
      {
        header: "Org Name",
        accessorKey: "org_name",
        cell: (ctx) => <span className="text-zinc-300">{ctx.getValue() ? String(ctx.getValue()) : "—"}</span>,
      },
      { header: "Total Tokens", accessorKey: "total_tokens" },
      { header: "Prompt Tokens", accessorKey: "prompt_tokens" },
      { header: "Completion Tokens", accessorKey: "completion_tokens" },
      { header: "API Calls", accessorKey: "call_count" },
      {
        header: "Cache Hits %",
        accessorKey: "cache_hit_rate_percent",
        cell: (ctx) => fmtPct(ctx.getValue() as any),
      },
      {
        header: "Avg Latency ms",
        accessorKey: "avg_latency_ms",
        cell: (ctx) => {
          const v = ctx.getValue() as any;
          return v == null ? "—" : `${Math.round(Number(v))}`;
        },
      },
      {
        header: "Error Count",
        accessorKey: "errors",
        cell: (ctx) => fmtNum(ctx.getValue() as any),
      },
      {
        header: "Last Active",
        accessorKey: "last_active",
        cell: (ctx) => (ctx.getValue() ? String(ctx.getValue()) : "—"),
      },
      {
        header: "Actions",
        id: "actions",
        enableSorting: false,
        cell: (ctx) => {
          const orgId = ctx.row.original.org_id;
          const qs = new URLSearchParams({ period }).toString();
          return (
            <Button asChild variant="outline" className="border-white/10">
              <Link href={`/usage/${encodeURIComponent(orgId)}?${qs}`}>
                View Details
              </Link>
            </Button>
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
      "Org ID",
      "Org Name",
      "Total Tokens",
      "Prompt Tokens",
      "Completion Tokens",
      "API Calls",
      "Cache Hits %",
      "Avg Latency ms",
      "Error Count",
      "Last Active",
    ];
    const csvRows = rows.map((r) => ({
      "Org ID": r.org_id,
      "Org Name": r.org_name ?? "",
      "Total Tokens": r.total_tokens ?? "",
      "Prompt Tokens": r.prompt_tokens ?? "",
      "Completion Tokens": r.completion_tokens ?? "",
      "API Calls": r.call_count ?? "",
      "Cache Hits %": r.cache_hit_rate_percent ?? "",
      "Avg Latency ms": r.avg_latency_ms ?? "",
      "Error Count": r.errors ?? "",
      "Last Active": r.last_active ?? "",
    }));
    const csv = buildCsv(headers, csvRows);
    downloadCsv(`gisul-usage-${period}.csv`, csv);
  };

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40">
      <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <input
            className="h-9 w-full rounded-md border border-white/10 bg-zinc-950/40 px-3 text-sm text-zinc-200 outline-none focus:border-cyan-500/40 sm:w-[280px]"
            placeholder="Search org ID or name…"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="border-white/10" onClick={exportAll} disabled={rows.length === 0}>
            Export CSV
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="p-4">
          <Skeleton className="h-10 w-full" />
          <div className="mt-3 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        </div>
      ) : (
        <>
          <div className="overflow-auto">
            <table className="min-w-[1100px] w-full text-left text-sm">
              <thead className="text-xs text-zinc-500">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id} className="border-b border-white/10">
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        className={`px-4 py-2 ${h.column.getCanSort() ? "cursor-pointer select-none" : ""}`}
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {h.column.getCanSort() ? (
                            <span className="text-[10px] text-zinc-600">
                              {h.column.getIsSorted() === "asc"
                                ? "▲"
                                : h.column.getIsSorted() === "desc"
                                  ? "▼"
                                  : ""}
                            </span>
                          ) : null}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="text-zinc-200">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-10 text-center text-zinc-500" colSpan={columns.length}>
                      No usage data for this period.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((r) => (
                    <tr key={r.id} className="border-b border-white/5 hover:bg-white/5">
                      {r.getVisibleCells().map((c) => (
                        <td key={c.id} className="px-4 py-2">
                          {c.column.id === "total_tokens" ||
                          c.column.id === "prompt_tokens" ||
                          c.column.id === "completion_tokens" ||
                          c.column.id === "call_count" ? (
                            <span className="tabular-nums">{fmtNum(c.getValue() as any)}</span>
                          ) : (
                            flexRender(c.column.columnDef.cell, c.getContext())
                          )}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between gap-3 px-4 py-3 text-xs text-zinc-500">
            <div>
              Page{" "}
              <span className="font-medium text-zinc-300">
                {table.getState().pagination.pageIndex + 1}
              </span>{" "}
              of{" "}
              <span className="font-medium text-zinc-300">{table.getPageCount()}</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="border-white/10"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                Prev
              </Button>
              <Button
                variant="outline"
                className="border-white/10"
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

