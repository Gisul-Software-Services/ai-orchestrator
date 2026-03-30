"use client";

import { Collapsible } from "./Collapsible";
import { CodeBlock } from "./CodeBlock";
import { isRecord } from "./types";

export function EnrichDsaView({ p }: { p: Record<string, unknown> }) {
  const pub = Array.isArray(p.public_testcases) ? p.public_testcases : [];
  const hid = Array.isArray(p.hidden_testcases) ? p.hidden_testcases : [];
  const starter = p.starter_code;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <h4 className="mb-2 font-semibold text-zinc-100">DSA enrichment</h4>
      <p className="mb-3 text-sm text-zinc-400">
        Pipeline: <code className="text-zinc-300">{String(p.pipeline ?? "")}</code>
        {" · "}
        {String(p.test_case_source ?? "")}
      </p>
      {p.function_signature != null ? (
        <div className="mb-3">
          <Collapsible title="Function signature" defaultOpen>
            <pre className="overflow-x-auto text-xs text-zinc-300">
              {JSON.stringify(p.function_signature, null, 2)}
            </pre>
          </Collapsible>
        </div>
      ) : null}
      {pub.length > 0 && (
        <div className="mb-2">
          <Collapsible title={`Public test cases (${pub.length})`}>
            <pre className="max-h-48 overflow-auto text-xs text-zinc-400">
              {JSON.stringify(pub, null, 2)}
            </pre>
          </Collapsible>
        </div>
      )}
      {hid.length > 0 && (
        <p className="mb-2 text-xs text-zinc-500">{hid.length} hidden test case(s)</p>
      )}
      {isRecord(starter) && Object.keys(starter).length > 0 && (
        <Collapsible title="Starter code">
          <div className="space-y-2">
            {Object.entries(starter).map(([lang, code]) => (
              <div key={lang}>
                <p className="text-xs text-zinc-500">{lang}</p>
                <CodeBlock code={String(code)} language={lang} />
              </div>
            ))}
          </div>
        </Collapsible>
      )}
    </div>
  );
}
