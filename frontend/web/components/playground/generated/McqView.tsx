"use client";

import { Collapsible } from "./Collapsible";
import { isRecord } from "./types";

export function McqView({ q, index }: { q: Record<string, unknown>; index: number }) {
  const options = Array.isArray(q.options) ? q.options : [];
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">Question {index}</h4>
      <p className="mb-3 whitespace-pre-wrap text-zinc-300">
        {String(q.question ?? "*(no question)*")}
      </p>
      <ul className="space-y-1">
        {options.map((opt, i) => {
          if (!isRecord(opt)) return null;
          const label = String(opt.label ?? "?");
          const text = String(opt.text ?? "");
          const correct = Boolean(opt.isCorrect);
          return (
            <li
              key={i}
              className={
                correct
                  ? "font-medium text-emerald-300"
                  : "text-zinc-400"
              }
            >
              {label}. {correct ? "✅ " : ""}
              {text}
            </li>
          );
        })}
      </ul>
      {q.explanation != null && String(q.explanation).length > 0 ? (
        <div className="mt-3">
          <Collapsible title="💡 Explanation">
            <p className="whitespace-pre-wrap text-sm text-zinc-300">
              {String(q.explanation)}
            </p>
          </Collapsible>
        </div>
      ) : null}
      <div className="mt-3 flex gap-4 text-xs text-zinc-500">
        <span>Difficulty: {String(q.difficulty ?? "—")}</span>
        <span>Bloom: {String(q.bloomLevel ?? "—")}</span>
      </div>
    </div>
  );
}
