"use client";

import { Fragment, useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type { RequestLogItem } from "@/hooks/useHistory";
import { Button } from "@/components/ui/button";
import { RequestRowDetail } from "@/components/history/RequestRowDetail";

function methodCls(m: string) {
  const t = m.toUpperCase();
  if (t === "GET") return "bg-sky-500/15 text-sky-200 border-sky-500/25";
  if (t === "POST") return "bg-emerald-500/15 text-emerald-200 border-emerald-500/25";
  return "bg-zinc-500/15 text-zinc-200 border-zinc-500/25";
}

function statusCls(code: number) {
  if (code >= 500) return "text-red-300";
  if (code >= 300) return "text-amber-300";
  return "text-emerald-300";
}

export function RequestLogTable({
  items,
  total,
  page,
  pageSize,
  onPageChange,
  sortBy,
  sortOrder,
  onSortChange,
}: {
  items: RequestLogItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  sortBy: "timestamp" | "latency_ms";
  sortOrder: "asc" | "desc";
  onSortChange: (s: { sortBy: "timestamp" | "latency_ms"; sortOrder: "asc" | "desc" }) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const columns: ColumnDef<RequestLogItem>[] = [
    {
      header: "Timestamp",
      id: "timestamp",
      cell: (ctx) => new Date(String(ctx.row.original.timestamp)).toLocaleString(),
    },
    {
      header: "Method",
      accessorKey: "method",
      cell: (ctx) => (
        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${methodCls(String(ctx.getValue()))}`}>
          {String(ctx.getValue())}
        </span>
      ),
    },
    {
      header: "Path",
      accessorKey: "path",
      cell: (ctx) => {
        const p = String(ctx.getValue());
        const short = p.length > 56 ? `${p.slice(0, 56)}…` : p;
        return (
          <span title={p} className="font-mono text-xs text-zinc-300">
            {short}
          </span>
        );
      },
    },
    { header: "Org ID", accessorKey: "org_id" },
    {
      header: "Status",
      accessorKey: "status_code",
      cell: (ctx) => (
        <span className={statusCls(Number(ctx.getValue()))}>{Number(ctx.getValue())}</span>
      ),
    },
    { header: "Latency ms", accessorKey: "latency_ms" },
    {
      header: "Cache Hit",
      accessorKey: "cache_hit",
      cell: (ctx) =>
        ctx.getValue() ? (
          <span className="inline-flex rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-200">HIT</span>
        ) : (
          <span className="inline-flex rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-zinc-300">MISS</span>
        ),
    },
    {
      header: "Job ID",
      accessorKey: "job_id",
      cell: (ctx) => {
        const v = ctx.getValue() as string | null;
        if (!v) return <span className="text-zinc-500">—</span>;
        const short = v.length > 10 ? `${v.slice(0, 10)}…` : v;
        return (
          <button
            type="button"
            className="font-mono text-xs text-cyan-300 hover:underline"
            title={v}
            onClick={() => navigator.clipboard.writeText(v)}
          >
            {short}
          </button>
        );
      },
    },
  ];

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40">
      <div className="flex items-center justify-end gap-2 border-b border-white/10 px-4 py-2 text-xs">
        <Button
          variant="outline"
          className="border-white/10"
          onClick={() =>
            onSortChange({
              sortBy: "timestamp",
              sortOrder: sortBy === "timestamp" && sortOrder === "asc" ? "desc" : "asc",
            })
          }
        >
          Sort timestamp
        </Button>
        <Button
          variant="outline"
          className="border-white/10"
          onClick={() =>
            onSortChange({
              sortBy: "latency_ms",
              sortOrder: sortBy === "latency_ms" && sortOrder === "asc" ? "desc" : "asc",
            })
          }
        >
          Sort latency
        </Button>
      </div>
      <div className="overflow-auto">
        <table className="min-w-[1100px] w-full text-left text-sm">
          <thead className="text-xs text-zinc-500">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-white/10">
                {hg.headers.map((h) => (
                  <th key={h.id} className="px-4 py-2">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="text-zinc-200">
            {table.getRowModel().rows.map((r) => (
              <Fragment key={r.id}>
                <tr
                  className="cursor-pointer border-b border-white/5 hover:bg-white/5"
                  onClick={() =>
                    setExpanded(expanded === r.original.request_id ? null : r.original.request_id)
                  }
                >
                  {r.getVisibleCells().map((c) => (
                    <td key={c.id} className="px-4 py-2">
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
                {expanded === r.original.request_id ? (
                  <tr key={`${r.id}-detail`} className="border-b border-white/5 bg-white/5">
                    <td colSpan={columns.length} className="px-4 py-3">
                      <RequestRowDetail item={r.original} />
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3 px-4 py-3 text-xs text-zinc-500">
        <div>
          Page <span className="text-zinc-300">{page}</span> of{" "}
          <span className="text-zinc-300">{totalPages}</span>
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
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

