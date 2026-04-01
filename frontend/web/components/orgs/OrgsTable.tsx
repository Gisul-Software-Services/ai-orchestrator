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
import { useOrgProfileQuery } from "@/hooks/useOrgs";

export type OrgListRow = {
  org_id: string;
  total_tokens: number;
  call_count: number;
};

function OrgNameCell({ orgId }: { orgId: string }) {
  const q = useOrgProfileQuery(orgId);
  if (q.isLoading) return <span className="text-zinc-500">…</span>;
  if (q.isError) return <span className="text-zinc-500">-</span>;
  return <span>{String((q.data as any)?.name ?? "-")}</span>;
}

export function OrgsTable({ rows }: { rows: OrgListRow[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns: ColumnDef<OrgListRow>[] = [
    {
      header: "Org ID",
      accessorKey: "org_id",
      cell: (ctx) => <span className="font-mono">{String(ctx.getValue())}</span>,
    },
    {
      header: "Org Name",
      id: "org_name",
      cell: (ctx) => <OrgNameCell orgId={ctx.row.original.org_id} />,
    },
    {
      header: "Total Tokens",
      accessorKey: "total_tokens",
      cell: (ctx) => Number(ctx.getValue() ?? 0).toLocaleString(),
    },
    {
      header: "API Calls",
      accessorKey: "call_count",
      cell: (ctx) => Number(ctx.getValue() ?? 0).toLocaleString(),
    },
    {
      header: "Keys",
      id: "keys",
      enableSorting: false,
      cell: () => <span className="text-zinc-400">View</span>,
    },
    {
      header: "Actions",
      id: "actions",
      enableSorting: false,
      cell: (ctx) => (
        <Button asChild variant="outline" className="border-white/10">
          <Link href={`/orgs/${encodeURIComponent(ctx.row.original.org_id)}`}>Manage</Link>
        </Button>
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
    <div className="rounded-xl border border-white/10 bg-zinc-950/40">
      <div className="border-b border-white/10 px-4 py-3">
        <input
          className="h-9 w-full max-w-[280px] rounded-md border border-white/10 bg-zinc-950/40 px-3 text-sm text-zinc-200 outline-none focus:border-cyan-500/40"
          placeholder="Search org ID…"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
      </div>
      <div className="overflow-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="text-xs text-zinc-500">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-white/10">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    className={`px-4 py-2 ${h.column.getCanSort() ? "cursor-pointer select-none" : ""}`}
                    onClick={h.column.getToggleSortingHandler()}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="text-zinc-200">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-zinc-500">
                  No organisations found.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((r) => (
                <tr key={r.id} className="border-b border-white/5 hover:bg-white/5">
                  {r.getVisibleCells().map((c) => (
                    <td key={c.id} className="px-4 py-2">
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

