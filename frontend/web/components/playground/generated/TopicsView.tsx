"use client";

import { isRecord } from "./types";

export function TopicsView({ topics }: { topics: unknown[] }) {
  return (
    <div className="space-y-2">
      {topics.map((t, i) => {
        const index = i + 1;
        if (isRecord(t)) {
          const label = String(t.label ?? t);
          const qtype = String(t.questionType ?? "");
          const diff = String(t.difficulty ?? "");
          const judge = t.canUseJudge0;
          return (
            <div
              key={i}
              className="flex flex-wrap items-baseline gap-3 border-b border-zinc-800/80 py-2"
            >
              <span className="font-medium text-zinc-100">
                {index}. {label}
              </span>
              {qtype && (
                <span className="text-xs text-zinc-500">Type: {qtype}</span>
              )}
              {diff && (
                <span className="text-xs text-zinc-500">Difficulty: {diff}</span>
              )}
              {judge !== undefined && (
                <span className="text-xs text-zinc-500">
                  Judge0 {judge ? "✅" : ""}
                </span>
              )}
            </div>
          );
        }
        return (
          <div key={i} className="text-zinc-300">
            {index}. {String(t)}
          </div>
        );
      })}
    </div>
  );
}
