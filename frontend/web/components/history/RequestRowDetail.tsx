"use client";

import type { RequestLogItem } from "@/hooks/useHistory";

export function RequestRowDetail({ item }: { item: RequestLogItem }) {
  const keys = Object.keys(item).sort();
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-3 text-xs">
      <div className="mb-2 font-medium text-zinc-300">Request details</div>
      <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
        {keys.map((k) => (
          <div key={k} className="flex gap-2">
            <span className="min-w-[110px] font-mono text-zinc-500">{k}</span>
            <span className="break-all text-zinc-300">
              {typeof item[k] === "object" ? JSON.stringify(item[k]) : String(item[k])}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

