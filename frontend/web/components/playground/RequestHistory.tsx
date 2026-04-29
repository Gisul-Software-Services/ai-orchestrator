"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Check, ChevronDown, ChevronUp, Clock, Copy, History } from "lucide-react";

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
    <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/50 backdrop-blur-sm">
      <div className="flex items-center gap-2 border-b border-zinc-800/60 px-5 py-3.5">
        <History className="h-4 w-4 text-zinc-500" strokeWidth={1.5} />
        <div className="text-sm font-semibold text-zinc-100">Session history</div>
        {items.length > 0 && (
          <span className="ml-auto rounded-full border border-zinc-700/60 bg-zinc-800/60 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
            {items.length}
          </span>
        )}
      </div>

      <div className="p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <Clock className="h-8 w-8 text-zinc-700" strokeWidth={1} />
            <div className="text-sm text-zinc-500">No runs yet</div>
            <div className="text-xs text-zinc-700">Generate something to see history here</div>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((it, idx) => (
              <HistoryRow
                key={`${it.timestamp}-${idx}`}
                item={it}
                active={selectedIndex === idx}
                onClick={() => onSelect(idx)}
              />
            ))}
          </div>
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
  const [copied, setCopied] = useState(false);

  function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    const text = JSON.stringify(
      { request: item.payload, response: item.result },
      null,
      2
    );
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className={cn(
      "overflow-hidden rounded-xl border transition-colors",
      active ? "border-cyan-500/30 bg-cyan-500/5" : "border-zinc-800/60 bg-zinc-950/30"
    )}>
      <button
        type="button"
        onClick={() => { onClick(); setOpen((v) => !v); }}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={cn(
            "h-2 w-2 shrink-0 rounded-full",
            active ? "bg-cyan-400" : "bg-zinc-600"
          )} />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-zinc-200">{item.endpoint}</div>
            <div className="text-xs text-zinc-500">
              {new Date(item.timestamp).toLocaleTimeString()} · {item.durationSeconds.toFixed(1)}s
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Copy button — copies request + response as one JSON object */}
          <span
            role="button"
            tabIndex={0}
            onClick={handleCopy}
            onKeyDown={(e) => e.key === "Enter" && handleCopy(e as any)}
            title="Copy request + response"
            className={cn(
              "flex items-center gap-1 rounded-lg border px-2 py-1 text-[10px] font-medium transition-all",
              copied
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                : "border-zinc-700/60 bg-zinc-800/60 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300"
            )}
          >
            {copied
              ? <><Check className="h-3 w-3" />Copied</>
              : <><Copy className="h-3 w-3" />Copy</>
            }
          </span>
          <span className="text-zinc-600">
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-zinc-800/60 px-4 pb-4 pt-3 space-y-3">
          <div>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Request</div>
            <pre className="max-h-[200px] overflow-auto rounded-lg border border-zinc-800/60 bg-zinc-950/60 p-3 text-xs text-zinc-400 leading-relaxed">
              {JSON.stringify(item.payload, null, 2)}
            </pre>
          </div>
          <div>
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">Response</div>
            <pre className="max-h-[300px] overflow-auto rounded-lg border border-zinc-800/60 bg-zinc-950/60 p-3 text-xs text-zinc-400 leading-relaxed">
              {JSON.stringify(item.result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
