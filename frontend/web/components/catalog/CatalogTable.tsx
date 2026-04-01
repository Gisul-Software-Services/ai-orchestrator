"use client";

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
import type { CatalogEntry } from "@/hooks/useCatalog";

function categoryColor(c: string) {
  switch (c) {
    case "tabular":
      return "bg-sky-500/15 text-sky-200 border-sky-500/25";
    case "nlp":
      return "bg-violet-500/15 text-violet-200 border-violet-500/25";
    case "cv":
      return "bg-emerald-500/15 text-emerald-200 border-emerald-500/25";
    case "audio":
      return "bg-orange-500/15 text-orange-200 border-orange-500/25";
    case "time-series":
      return "bg-yellow-500/15 text-yellow-200 border-yellow-500/25";
    case "graph":
      return "bg-pink-500/15 text-pink-200 border-pink-500/25";
    default:
      return "bg-white/5 text-zinc-200 border-white/10";
  }
}

export function CatalogTable({
  rows,
  onEdit,
  onDelete,
  onRowClick,
}: {
  rows: CatalogEntry[];
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onRowClick: (id: string) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "name", desc: false },
  ]);

  const columns = useMemo<ColumnDef<CatalogEntry>[]>(
    () => [
      {
        header: "Name",
        accessorKey: "name",
        cell: (ctx) => (
          <button
            type="button"
            className="text-left font-medium text-cyan-200 hover:underline"
            onClick={() => onRowClick(ctx.row.original.id)}
          >
            {String(ctx.getValue())}
          </button>
        ),
      },
      { header: "ID", accessorKey: "id", cell: (ctx) => <span className="font-mono text-xs">{String(ctx.getValue())}</span> },
      {
        header: "Category",
        accessorKey: "category",
        cell: (ctx) => (
          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${categoryColor(String(ctx.getValue()))}`}>
            {String(ctx.getValue())}
          </span>
        ),
      },
      { header: "Domain", accessorKey: "domain" },
      { header: "Source", accessorKey: "source" },
      { header: "Size", accessorKey: "size" },
      {
        header: "Difficulty",
        accessorKey: "difficulty",
        cell: (ctx) => {
          const d = (ctx.getValue() as any) as string[];
          return (
            <div className="flex flex-wrap gap-1">
              {(Array.isArray(d) ? d : []).map((x) => (
                <span key={x} className="inline-flex rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-zinc-200">
                  {x}
                </span>
              ))}
            </div>
          );
        },
      },
      {
        header: "Direct Load",
        accessorKey: "direct_load",
        cell: (ctx) => (ctx.getValue() ? "yes" : "no"),
      },
      {
        header: "Tags",
        accessorKey: "tags",
        enableSorting: false,
        cell: (ctx) => {
          const t = (ctx.getValue() as any) as string[];
          const tags = Array.isArray(t) ? t : [];
          const shown = tags.slice(0, 3);
          const more = tags.length - shown.length;
          return (
            <div className="text-xs text-zinc-300">
              {shown.join(", ")}
              {more > 0 ? <span className="text-zinc-500"> +{more} more</span> : null}
            </div>
          );
        },
      },
      {
        header: "Actions",
        id: "actions",
        enableSorting: false,
        cell: (ctx) => (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              className="border-white/10"
              onClick={() => onEdit(ctx.row.original.id)}
            >
              Edit
            </Button>
            <Button
              variant="outline"
              className="border-red-500/30 text-red-200 hover:bg-red-500/10"
              onClick={() => onDelete(ctx.row.original.id)}
            >
              Delete
            </Button>
          </div>
        ),
      },
    ],
    [onDelete, onEdit, onRowClick]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40">
      <div className="overflow-auto">
        <table className="min-w-[1200px] w-full text-left text-sm">
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
                <td colSpan={columns.length} className="px-4 py-10 text-center text-zinc-500">
                  No datasets match your filters.
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
    </div>
  );
}

