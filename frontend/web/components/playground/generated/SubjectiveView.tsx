"use client";

import { Collapsible } from "./Collapsible";

export function SubjectiveView({
  q,
  index,
}: {
  q: Record<string, unknown>;
  index: number;
}) {
  const criteria = Array.isArray(q.gradingCriteria) ? q.gradingCriteria : [];
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">Question {index}</h4>
      <p className="mb-3 whitespace-pre-wrap text-zinc-300">
        {String(q.question ?? "*(no question)*")}
      </p>
      {q.expectedAnswer != null && String(q.expectedAnswer).length > 0 ? (
        <Collapsible title="📝 Expected answer">
          <p className="whitespace-pre-wrap text-sm text-emerald-200/90">
            {String(q.expectedAnswer)}
          </p>
        </Collapsible>
      ) : null}
      {criteria.length > 0 && (
        <div className="mt-2">
          <Collapsible title="📏 Grading criteria">
            <ul className="list-inside list-disc text-sm text-zinc-300">
              {criteria.map((c, i) => (
                <li key={i}>{String(c)}</li>
              ))}
            </ul>
          </Collapsible>
        </div>
      )}
      <div className="mt-3 flex gap-4 text-xs text-zinc-500">
        <span>Difficulty: {String(q.difficulty ?? "—")}</span>
        <span>Bloom: {String(q.bloomLevel ?? "—")}</span>
      </div>
    </div>
  );
}
