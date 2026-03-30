"use client";

import { isRecord } from "./types";

export function MetadataBar({ data }: { data: unknown }) {
  if (!isRecord(data)) return null;
  const t = data.generation_time_seconds;
  const hasMeta =
    t !== undefined || data.batch_size !== undefined || data.cache_hit !== undefined;
  if (!hasMeta) return null;
  return (
    <div className="mt-6 flex flex-wrap gap-4 rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3 text-sm">
      {typeof t === "number" && (
        <span className="text-zinc-300">
          ⏱ <span className="text-zinc-500">Time</span>{" "}
          <strong>{t.toFixed(2)}s</strong>
        </span>
      )}
      {data.batch_size !== undefined && (
        <span className="text-zinc-300">
          📦 <span className="text-zinc-500">Batch</span>{" "}
          <strong>{String(data.batch_size)}</strong>
        </span>
      )}
      {data.cache_hit !== undefined && (
        <span className="text-zinc-300">
          🗃 <span className="text-zinc-500">Cache</span>{" "}
          <strong>{data.cache_hit ? "Hit" : "Miss"}</strong>
        </span>
      )}
    </div>
  );
}
