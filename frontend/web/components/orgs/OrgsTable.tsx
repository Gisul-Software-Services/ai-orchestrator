"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { useOrgProfileQuery, useOrgKeysQuery } from "@/hooks/useOrgs";
import { cn } from "@/lib/utils";
import { Key, ArrowUpDown, ChevronUp, ChevronDown } from "lucide-react";

export type OrgListRow = {
  org_id: string;
  total_tokens: number;
  call_count: number;
};

// ── Per-org enrichment cells ──────────────────────────────────────────────────

function OrgNameCell({ orgId }: { orgId: string }) {
  const q = useOrgProfileQuery(orgId);
  if (q.isLoading) {
    return <span className="inline-block h-3 w-20 animate-pulse rounded bg-zinc-800" />;
  }
  if (q.isError) {
    return <span className="text-zinc-600">—</span>;
  }
  // Profile can return { name, orgName, org: { name } } depending on backend version
  const d = q.data as Record<string, unknown> | null;
  const name =
    (d?.name as string | undefined) ??
    (d?.orgName as string | undefined) ??
    ((d?.org as Record<string, unknown> | undefined)?.name as string | undefined) ??
    null;
  if (!name) return <span className="text-zinc-600">—</span>;
  return <span className="font-medium text-zinc-200">{name}</span>;
}

function KeyCountCell({ orgId }: { orgId: string }) {
  const q = useOrgKeysQuery(orgId);
  if (q.isLoading) {
    return <span className="inline-block h-3 w-8 animate-pulse rounded bg-zinc-800" />;
  }
  if (q.isError) {
    return <span className="text-zinc-600">—</span>;
  }
  const keys = q.data?.keys ?? [];
  const active = keys.filter((k) => k.status !== "revoked").length;
  const total = keys.length;
  return (
    <div className="flex items-center gap-1.5">
      <Key className="h-3 w-3 text-zinc-600" />
      <span className={cn("text-sm font-medium tabular-nums", active > 0 ? "text-emerald-400" : "text-zinc-500")}>
        {active}
      </span>
      {total > active && (
        <span className="text-xs text-zinc-600">/ {total}</span>
      )}
    </div>
  );
}

// ── Main table ────────────────────────────────────────────────────────────────

export function OrgsTable({ rows }: { rows: OrgListRow[] }) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "total_tokens", desc: true },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns: ColumnDef<OrgListRow>[] = [
    {
      header: "Org ID",
      accessorKey: "org_id",
      cell: (ctx) => (
        <span className="font-mono text-xs text-zinc-300">{String(ctx.getValue())}</span>
      ),
    },
    {
      header: "Org Name",
      id: "org_name",
      enableSorting: false,
      cell: (ctx) => <OrgNameCell orgId={ctx.row.original.org_id} />,
    },
    {
      header: "Total Tokens",
      accessorKey: "total_tokens",
      cell: (ctx) => (
        <span className="tabular-nums font-medium text-console-accent">
          {Number(ctx.getValue() ?? 0).toLocaleString()}
        </span>
      ),
    },
    {
      header: "API Calls",
      accessorKey: "call_count",
      cell: (ctx) => (
        <span className="tabular-nums text-zinc-300">
          {Number(ctx.getValue() ?? 0).toLocaleString()}
        </span>
      ),
    },
    {
      header: "Active Keys",
      id: "keys",
      enableSorting: false,
      cell: (ctx) => <KeyCountCell orgId={ctx.row.original.org_id} />,
    },
    {
      header: "Actions",
      id: "actions",
      enableSorting: false,
      cell: (ctx) => (
        <Link
          href={`/orgs/${encodeURIComponent(ctx.row.original.org_id)}`}
          className="inline-flex items-center gap-1 rounded-lg border border-zinc-700/60 bg-zinc-900 px-2.5 py-1 text-xs font-medium text-zinc-300 transition-colors hover:border-cyan-500/40 hover:text-console-accent"
        >
          Manage →
        </Link>
      ),
    },
  ];

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, _col, filter) => {
      const q = String(filter ?? "").toLowerCase().trim();
      if (!q) return true;
      return row.original.org_id.toLowerCase().includes(q);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 backdrop-blur-sm">
      {/* Toolbar */}
      <div className="border-b border-zinc-800/60 px-4 py-3">
        <input
          className="h-9 w-full max-w-[280px] rounded-lg border border-zinc-700/60 bg-zinc-950/60 px-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-cyan-500/40"
          placeholder="Search org ID…"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
      </div>

      <div className="overflow-auto">
        <table className="w-full min-w-[800px] text-left text-sm">
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
                <td colSpan={columns.length} className="px-4 py-10 text-center text-sm text-zinc-600">
                  No organisations found.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-zinc-800/40 transition-colors hover:bg-zinc-800/30"
                >
                  {r.getVisibleCells().map((c) => (
                    <td key={c.id} className="px-4 py-3">
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="border-t border-zinc-800/60 px-4 py-2.5 text-xs text-zinc-600">
        {table.getFilteredRowModel().rows.length} organisation{table.getFilteredRowModel().rows.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
