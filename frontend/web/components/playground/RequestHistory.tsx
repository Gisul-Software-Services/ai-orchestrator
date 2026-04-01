"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { CodeBlock } from "@/components/playground/generated/CodeBlock";

export interface HistoryItem {
  timestamp: number;
  endpoint: string;
  payload: unknown;
  result: unknown;
  durationSeconds: number;
}

export function RequestHistory({
  items,
  onSelect,
  selectedIndex,
}: {
  items: HistoryItem[];
  selectedIndex: number | null;
  onSelect: (idx: number) => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-3 text-sm font-semibold text-zinc-50">
        Session history
      </div>
      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="text-sm text-zinc-500">No runs yet.</div>
        ) : (
          items.map((it, idx) => (
            <HistoryRow
              key={it.timestamp + ":" + idx}
              item={it}
              active={selectedIndex === idx}
              onClick={() => onSelect(idx)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function HistoryRow({
  item,
  active,
  onClick,
}: {
  item: HistoryItem;
  active: boolean;
  onClick: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn("rounded-lg border border-zinc-800", active && "border-cyan-500/50")}>
      <button
        type="button"
        onClick={() => {
          onClick();
          setOpen((v) => !v);
        }}
        className="flex w-full items-center justify-between gap-3 bg-zinc-900/40 px-3 py-2 text-left"
      >
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-zinc-100">
            {item.endpoint}
          </div>
          <div className="text-xs text-zinc-400">
            {new Date(item.timestamp).toLocaleString()} • {item.durationSeconds.toFixed(1)}s
          </div>
        </div>
        <div className="text-xs text-zinc-400">{open ? "Hide" : "View"}</div>
      </button>
      {open ? (
        <div className="space-y-3 p-3">
          <div>
            <div className="mb-1 text-xs font-medium text-zinc-400">Request</div>
            <CodeBlock code={JSON.stringify(item.payload, null, 2)} />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-zinc-400">Response</div>
            <CodeBlock code={JSON.stringify(item.result, null, 2)} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

