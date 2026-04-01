"use client";

import { Button } from "@/components/ui/button";

export type HistoryFilters = {
  endpoint: string;
  org_id: string;
  status: "all" | "success" | "error";
  start_date: string;
  end_date: string;
};

export function LogFilters({
  value,
  onChange,
  onClear,
}: {
  value: HistoryFilters;
  onChange: (v: HistoryFilters) => void;
  onClear: () => void;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">
        <div className="lg:col-span-2">
          <label className="text-xs text-zinc-500">Path / endpoint</label>
          <input
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.endpoint}
            onChange={(e) => onChange({ ...value, endpoint: e.target.value })}
          />
        </div>
        <div>
          <label className="text-xs text-zinc-500">Org ID</label>
          <input
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.org_id}
            onChange={(e) => onChange({ ...value, org_id: e.target.value })}
          />
        </div>
        <div>
          <label className="text-xs text-zinc-500">Status</label>
          <select
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.status}
            onChange={(e) => onChange({ ...value, status: e.target.value as any })}
          >
            <option value="all">All</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-zinc-500">Start date</label>
          <input
            type="date"
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.start_date}
            onChange={(e) => onChange({ ...value, start_date: e.target.value })}
          />
        </div>
        <div>
          <label className="text-xs text-zinc-500">End date</label>
          <input
            type="date"
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.end_date}
            onChange={(e) => onChange({ ...value, end_date: e.target.value })}
          />
        </div>
      </div>
      <div className="mt-3 flex justify-end">
        <Button variant="outline" className="border-white/10" onClick={onClear}>
          Clear filters
        </Button>
      </div>
    </div>
  );
}

