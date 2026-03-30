"use client";

import { Collapsible } from "./Collapsible";
import { CodeBlock } from "./CodeBlock";
import { isRecord } from "./types";

function getSchema(p: Record<string, unknown>): unknown {
  if ("schema" in p) return p.schema;
  if ("sql_schema" in p) return p.sql_schema;
  return null;
}

export function SqlView({
  p,
  index,
}: {
  p: Record<string, unknown>;
  index: number;
}) {
  const schema = getSchema(p);
  const tables =
    isRecord(schema) && Array.isArray(schema.tables)
      ? schema.tables
      : [];

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">SQL problem {index}</h4>
      <p className="mb-4 whitespace-pre-wrap text-zinc-300">
        {String(p.problemStatement ?? "")}
      </p>
      {tables.length > 0 && (
        <div className="mb-2">
          <Collapsible title="🗂 Schema" defaultOpen>
            <div className="space-y-4">
              {tables.map((t, i) => {
                if (!isRecord(t)) return null;
                const cols = Array.isArray(t.columns) ? t.columns : [];
                return (
                  <div key={i}>
                    <p className="mb-1 text-sm font-medium text-zinc-300">
                      Table: {String(t.name ?? "?")}
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-zinc-700 text-zinc-500">
                            <th className="py-1 pr-2">Column</th>
                            <th className="py-1">Type</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cols.map((col, j) => {
                            if (!isRecord(col)) return null;
                            return (
                              <tr key={j} className="border-b border-zinc-800/80">
                                <td className="py-1 pr-2 font-mono">
                                  {String(col.name ?? col.column ?? "")}
                                </td>
                                <td className="py-1 text-zinc-400">
                                  {String(col.type ?? "")}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>
          </Collapsible>
        </div>
      )}
      {p.expectedQuery != null && String(p.expectedQuery).length > 0 ? (
        <div className="mb-2">
          <Collapsible title="✅ Expected query" defaultOpen>
            <CodeBlock code={String(p.expectedQuery)} language="sql" />
          </Collapsible>
        </div>
      ) : null}
      {p.explanation != null && String(p.explanation).length > 0 ? (
        <div className="mb-2">
          <Collapsible title="💡 Explanation">
            <p className="whitespace-pre-wrap text-sm text-zinc-300">
              {String(p.explanation)}
            </p>
          </Collapsible>
        </div>
      ) : null}
      {p.alternativeApproach != null && String(p.alternativeApproach).length > 0 ? (
        <Collapsible title="⚠️ Alternative approach">
          <p className="whitespace-pre-wrap text-sm text-zinc-400">
            {String(p.alternativeApproach)}
          </p>
        </Collapsible>
      ) : null}
      {Array.isArray(p.concepts_tested) && p.concepts_tested.length > 0 && (
        <p className="mt-2 text-xs text-zinc-500">
          Concepts: {p.concepts_tested.map(String).join(", ")}
        </p>
      )}
      <p className="mt-2 text-xs text-zinc-500">
        Difficulty: {String(p.difficulty ?? "—")}
      </p>
    </div>
  );
}
