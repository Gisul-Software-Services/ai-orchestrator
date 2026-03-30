"use client";

import { useMemo } from "react";
import { listRunHistory, type RunHistoryEntry } from "@/lib/playgroundRunHistory";

export function HistoryClient() {
  const runs = useMemo(() => listRunHistory(), []);

  if (runs.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-8 text-center text-sm text-zinc-500">
        No runs in this tab yet. Use the Playground and click Generate — runs appear
        here and in the playground sidebar.
        <div className="mt-4">
          <a href="/playground" className="text-console-accent hover:underline">
            Go to Playground
          </a>
        </div>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {runs.map((r) => (
        <li
          key={r.id}
          className="rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-4 text-sm"
        >
          <RunRow entry={r} />
        </li>
      ))}
    </ul>
  );
}

function RunRow({ entry }: { entry: RunHistoryEntry }) {
  const ok = !entry.error;
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <span
          className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
            ok ? "bg-emerald-950/50 text-emerald-300" : "bg-red-950/50 text-red-300"
          }`}
        >
          {ok ? "OK" : "Error"}
        </span>
        <p className="mt-2 font-mono text-[11px] text-zinc-500">{entry.postUrl}</p>
        <p className="mt-1 text-zinc-300">{entry.formSummary}</p>
        {entry.jobId && (
          <p className="mt-1 text-xs text-zinc-500">Job: {entry.jobId}</p>
        )}
      </div>
      <div className="text-right text-xs text-zinc-500">
        {new Date(entry.at).toLocaleString()}
        <br />
        {Math.round(entry.durationMs)} ms
      </div>
    </div>
  );
}
