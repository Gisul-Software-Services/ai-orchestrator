"use client";

import { Collapsible } from "./Collapsible";
import { CodeBlock } from "./CodeBlock";
import { isRecord } from "./types";

export function CodingView({
  p,
  index,
}: {
  p: Record<string, unknown>;
  index: number;
}) {
  const examples = Array.isArray(p.examples) ? p.examples : [];
  const testCases = Array.isArray(p.testCases) ? p.testCases : [];
  const constraints = Array.isArray(p.constraints) ? p.constraints : [];
  const hints = Array.isArray(p.hints) ? p.hints : [];
  const lang = String(p.language ?? "Python");

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">Problem {index}</h4>
      <p className="mb-3 font-medium text-zinc-200">Problem statement</p>
      <p className="mb-4 whitespace-pre-wrap text-zinc-300">
        {String(p.problemStatement ?? "")}
      </p>
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-zinc-500">Input format</p>
          <p className="whitespace-pre-wrap text-sm text-zinc-300">
            {String(p.inputFormat ?? "")}
          </p>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-zinc-500">Output format</p>
          <p className="whitespace-pre-wrap text-sm text-zinc-300">
            {String(p.outputFormat ?? "")}
          </p>
        </div>
      </div>
      {constraints.length > 0 && (
        <div className="mb-2">
          <Collapsible title="📐 Constraints">
            <ul className="list-inside list-disc text-sm text-zinc-300">
              {constraints.map((c, i) => (
                <li key={i}>{String(c)}</li>
              ))}
            </ul>
          </Collapsible>
        </div>
      )}
      {examples.length > 0 && (
        <div className="mb-2">
          <Collapsible title={`📖 Examples (${examples.length})`}>
            <div className="space-y-3">
              {examples.map((ex, i) => {
                if (!isRecord(ex)) return null;
                return (
                  <div key={i} className="border-b border-zinc-800 pb-2 last:border-0">
                    <p className="text-xs text-zinc-500">
                      Input: <code>{String(ex.input ?? "")}</code>
                    </p>
                    <p className="text-xs text-zinc-500">
                      Output: <code>{String(ex.output ?? "")}</code>
                    </p>
                    {ex.explanation != null && String(ex.explanation).length > 0 ? (
                      <p className="mt-1 text-xs text-zinc-500">
                        {String(ex.explanation)}
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </Collapsible>
        </div>
      )}
      {p.starterCode != null && String(p.starterCode).length > 0 ? (
        <div className="mb-2">
          <Collapsible title="🖊 Starter code" defaultOpen>
            <CodeBlock
              code={String(p.starterCode)}
              language={lang.toLowerCase() === "python" ? "python" : "text"}
            />
          </Collapsible>
        </div>
      ) : null}
      {testCases.length > 0 && (
        <div className="mb-2">
          <Collapsible title={`🧪 Test cases (${testCases.length})`}>
            <pre className="max-h-48 overflow-auto text-xs text-zinc-400">
              {JSON.stringify(testCases, null, 2)}
            </pre>
          </Collapsible>
        </div>
      )}
      {hints.length > 0 && (
        <Collapsible title="💡 Hints">
          <ol className="list-inside list-decimal text-sm text-zinc-300">
            {hints.map((h, i) => (
              <li key={i}>{String(h)}</li>
            ))}
          </ol>
        </Collapsible>
      )}
      {p.expectedComplexity != null && String(p.expectedComplexity).length > 0 ? (
        <p className="mt-2 text-xs text-zinc-500">
          Expected complexity: {String(p.expectedComplexity)}
        </p>
      ) : null}
      <p className="mt-2 text-xs text-zinc-500">
        Difficulty: {String(p.difficulty ?? "—")}
      </p>
    </div>
  );
}
