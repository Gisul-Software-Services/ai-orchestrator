"use client";

import { Collapsible } from "./Collapsible";
import { CodeBlock } from "./CodeBlock";
import { isRecord } from "./types";

export function DsaView({ p, index }: { p: Record<string, unknown>; index: number }) {
  const examples = Array.isArray(p.examples) ? p.examples : [];
  const publicTc = Array.isArray(p.public_testcases) ? p.public_testcases : [];
  const hidden = Array.isArray(p.hidden_testcases) ? p.hidden_testcases : [];
  const starter = p.starter_code;
  const imgs = Array.isArray(p.example_images) ? p.example_images : [];

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">DSA problem {index}</h4>
      {p.reworded != null && String(p.reworded).length > 0 ? (
        <p className="mb-2 text-xs text-zinc-500">
          🔄 Reworded from: {String(p.original_title ?? "")}
        </p>
      ) : null}
      <p className="mb-1 text-sm font-medium text-zinc-400">Problem statement</p>
      <p className="mb-4 whitespace-pre-wrap text-zinc-300">
        {String(p.description ?? "")}
      </p>
      {Array.isArray(p.tags) && p.tags.length > 0 && (
        <p className="mb-3 text-xs text-zinc-500">
          Tags: {p.tags.map(String).join(", ")}
        </p>
      )}
      {imgs.length > 0 && (
        <div className="mb-3">
          <Collapsible title="🖼️ Example images" defaultOpen>
            <div className="flex flex-wrap gap-2">
              {imgs.map((url, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={i}
                  src={String(url)}
                  alt=""
                  className="max-h-48 rounded border border-zinc-700"
                />
              ))}
            </div>
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
                  <div key={i}>
                    <p className="text-xs text-zinc-500">
                      Example {String(ex.example_num ?? i + 1)}
                    </p>
                    <CodeBlock
                      code={String(ex.example_text ?? "")}
                      language="text"
                    />
                  </div>
                );
              })}
            </div>
          </Collapsible>
        </div>
      )}
      {isRecord(p.function_signature) && (
        <div className="mb-2">
          <Collapsible title="🔧 Function signature">
            <CodeBlock
              code={formatSignature(p.function_signature)}
              language="python"
            />
          </Collapsible>
        </div>
      )}
      {publicTc.length > 0 && (
        <div className="mb-2">
          <Collapsible title={`🧪 Public test cases (${publicTc.length})`}>
            <ul className="space-y-2 text-sm text-zinc-300">
              {publicTc.map((tc, i) => {
                if (!isRecord(tc)) return null;
                return (
                  <li key={i} className="border-b border-zinc-800/80 pb-2">
                    <span className="text-zinc-500">In:</span>{" "}
                    <code>{String(tc.input_raw ?? "")}</code>
                    <br />
                    <span className="text-zinc-500">Expected:</span>{" "}
                    <code>{String(tc.expected_output ?? "")}</code>
                  </li>
                );
              })}
            </ul>
          </Collapsible>
        </div>
      )}
      {hidden.length > 0 && (
        <p className="mb-3 rounded-md border border-blue-900/50 bg-blue-950/20 p-2 text-sm text-blue-200">
          🔒 {hidden.length} hidden test case(s)
        </p>
      )}
      {isRecord(starter) && Object.keys(starter).length > 0 && (
        <div className="mb-2">
          <Collapsible title={`🖊 Starter code (${Object.keys(starter).length} languages)`}>
            <div className="space-y-3">
              {Object.entries(starter).map(([lang, code]) => (
                <div key={lang}>
                  <p className="mb-1 text-xs font-medium text-zinc-500">{lang}</p>
                  <CodeBlock code={String(code)} language={lang} />
                </div>
              ))}
            </div>
          </Collapsible>
        </div>
      )}
      <div className="mt-2 flex gap-4 text-xs text-zinc-500">
        <span>Difficulty: {String(p.difficulty ?? "—")}</span>
        <span>AI generated: {p.ai_generated ? "✅" : "—"}</span>
      </div>
    </div>
  );
}

function formatSignature(fn: Record<string, unknown>): string {
  const params = Array.isArray(fn.parameters)
    ? (fn.parameters as unknown[])
        .filter(isRecord)
        .map((x) => `${String(x.name ?? "")}: ${String(x.type ?? "")}`)
        .join(", ")
    : "";
  return `def ${String(fn.name ?? "fn")}(${params}) -> ${String(fn.return_type ?? "Any")}`;
}
