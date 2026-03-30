"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Copy, Check } from "lucide-react";
import type { GenerateMeta } from "@/lib/generation";
import { AimlView } from "./AimlView";
import { CodingView } from "./CodingView";
import { DsaView } from "./DsaView";
import { EnrichDsaView } from "./EnrichDsaView";
import { McqView } from "./McqView";
import { MetadataBar } from "./MetadataBar";
import { SqlView } from "./SqlView";
import { SubjectiveView } from "./SubjectiveView";
import { TopicsView } from "./TopicsView";
import { isRecord } from "./types";

function RawJsonSection({ data }: { data: unknown }) {
  const json = useMemo(() => JSON.stringify(data, null, 2), [data]);
  const [url, setUrl] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [copied, setCopied] = useState(false);

  const display = useMemo(() => {
    const t = filter.trim().toLowerCase();
    if (!t) return json;
    return json
      .split("\n")
      .filter((line) => line.toLowerCase().includes(t))
      .join("\n");
  }, [json, filter]);

  useEffect(() => {
    const blob = new Blob([json], { type: "application/json" });
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => {
      URL.revokeObjectURL(u);
    };
  }, [json]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="mt-6 space-y-2">
      <details className="rounded-lg border border-zinc-800 bg-zinc-950/30">
        <summary className="cursor-pointer px-3 py-2 text-sm text-zinc-400">
          Raw JSON
        </summary>
        <div className="space-y-2 border-t border-zinc-800 p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="search"
              placeholder="Filter lines…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="min-w-0 flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-console-accent/30"
            />
            <button
              type="button"
              onClick={() => void copy()}
              className="inline-flex items-center justify-center gap-1.5 rounded-md border border-zinc-600 px-2.5 py-1.5 text-xs text-zinc-300 hover:bg-zinc-900"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" strokeWidth={2} />
              ) : (
                <Copy className="h-3.5 w-3.5" strokeWidth={2} />
              )}
              {copied ? "Copied" : "Copy all"}
            </button>
          </div>
          <pre className="max-h-64 overflow-auto rounded-md border border-zinc-800/80 bg-black/30 p-3 text-xs text-zinc-500">
            {display || "(no matching lines)"}
          </pre>
        </div>
      </details>
      {url && (
        <a
          href={url}
          download="generated_output.json"
          className="inline-block rounded-md border border-zinc-600 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-900"
        >
          ⬇️ Download JSON
        </a>
      )}
    </div>
  );
}

function RunMetaBar({ meta }: { meta: GenerateMeta }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-zinc-800/80 bg-zinc-950/60 px-3 py-2 text-xs text-zinc-500">
      <span>
        <span className="text-zinc-600">Time</span>{" "}
        <span className="font-mono text-zinc-300">{Math.round(meta.durationMs)} ms</span>
      </span>
      {meta.jobId != null && meta.jobId.length > 0 ? (
        <span>
          <span className="text-zinc-600">Job</span>{" "}
          <span className="font-mono text-zinc-400">{meta.jobId.slice(0, 12)}…</span>
        </span>
      ) : null}
      <span className="min-w-0 font-mono text-[10px] text-console-accent/80" title={meta.postUrl}>
        POST {meta.postUrl.replace(/^https?:\/\/[^/]+/, "")}
      </span>
    </div>
  );
}

export function GeneratedOutput({
  data,
  meta,
  orgIdForApi = "",
}: {
  data: unknown;
  meta?: GenerateMeta;
  orgIdForApi?: string;
}) {
  if (!isRecord(data)) {
    return (
      <div className="space-y-3 text-sm text-zinc-400">
        {meta && <RunMetaBar meta={meta} />}
        <pre className="overflow-auto rounded-lg border border-zinc-800 p-4 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  }

  const d = data;

  let body: ReactNode = null;
  let title = "📄 Generated output";

  if (Array.isArray(d.topics)) {
    title = `📋 Generated topics (${d.topics.length})`;
    body = <TopicsView topics={d.topics} />;
  } else if (Array.isArray(d.questions)) {
    title = `✅ Questions (${d.questions.length})`;
    body = (
      <div className="space-y-4">
        {d.questions.map((q, i) => {
          if (!isRecord(q)) return null;
          return "options" in q ? (
            <McqView key={i} q={q} index={i + 1} />
          ) : (
            <SubjectiveView key={i} q={q} index={i + 1} />
          );
        })}
      </div>
    );
  } else if (Array.isArray(d.coding_problems)) {
    title = `💻 Coding problems (${d.coding_problems.length})`;
    body = (
      <div className="space-y-4">
        {d.coding_problems.map((p, i) =>
          isRecord(p) ? <CodingView key={i} p={p} index={i + 1} /> : null
        )}
      </div>
    );
  } else if (Array.isArray(d.sql_problems)) {
    title = `🗄️ SQL problems (${d.sql_problems.length})`;
    body = (
      <div className="space-y-4">
        {d.sql_problems.map((p, i) =>
          isRecord(p) ? <SqlView key={i} p={p} index={i + 1} /> : null
        )}
      </div>
    );
  } else if (Array.isArray(d.aiml_problems)) {
    const lib = d.aiml_problems.some(
      (x) => isRecord(x) && x.dataset_strategy === "library"
    );
    title = lib
      ? `📚 AI/ML library problems (${d.aiml_problems.length})`
      : `🤖 AI/ML problems (${d.aiml_problems.length})`;
    body = (
      <div className="space-y-4">
        {d.aiml_problems.map((p, i) =>
          isRecord(p) ? (
            <AimlView key={i} p={p} index={i + 1} orgIdForApi={orgIdForApi} />
          ) : null
        )}
      </div>
    );
  } else if ("pipeline" in d && "function_signature" in d) {
    title = "🔧 DSA enrichment";
    body = <EnrichDsaView p={d} />;
  } else if (
    "public_testcases" in d &&
    "starter_code" in d &&
    !("pipeline" in d)
  ) {
    title = "🔢 DSA question";
    body = <DsaView p={d} index={1} />;
  } else if ("dataset" in d && "problemStatement" in d) {
    title = "🤖 AI/ML problem";
    body = <AimlView p={d} index={1} orgIdForApi={orgIdForApi} />;
  } else if ("options" in d && "question" in d) {
    title = "✅ MCQ question";
    body = isRecord(d) ? <McqView q={d} index={1} /> : null;
  } else if ("expectedAnswer" in d && "question" in d) {
    title = "✍️ Subjective question";
    body = isRecord(d) ? <SubjectiveView q={d} index={1} /> : null;
  } else if (
    ("schema" in d || "sql_schema" in d) &&
    "problemStatement" in d
  ) {
    title = "🗄️ SQL problem";
    body = isRecord(d) ? <SqlView p={d} index={1} /> : null;
  } else if ("inputFormat" in d && "problemStatement" in d) {
    title = "💻 Coding problem";
    body = isRecord(d) ? <CodingView p={d} index={1} /> : null;
  } else {
    body = (
      <div className="rounded-md border border-amber-900/40 bg-amber-950/20 p-3 text-sm text-amber-100">
        Unrecognised response shape — raw JSON below.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {meta && <RunMetaBar meta={meta} />}
      <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
      {body}
      <MetadataBar data={data} />
      <RawJsonSection data={data} />
    </div>
  );
}
