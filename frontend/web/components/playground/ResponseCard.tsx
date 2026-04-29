"use client";

import { useMemo, useState } from "react";
import { Check, Copy, Download, ChevronDown, ChevronUp } from "lucide-react";
import { GeneratedOutput } from "@/components/playground/generated/GeneratedOutput";
import { cn } from "@/lib/utils";

function downloadJson(filename: string, obj: unknown) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ResponseCard({
  endpoint,
  result,
  timestamp,
  durationSeconds,
}: {
  endpoint: string;
  result: unknown;
  timestamp: number;
  durationSeconds?: number;
}) {
  const tsLabel = useMemo(() => new Date(timestamp).toLocaleString(), [timestamp]);
  const [copied, setCopied] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative overflow-hidden rounded-2xl border border-zinc-800/60 bg-zinc-900/60 backdrop-blur-sm">
      {/* Top accent */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-500/10">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
          </div>
          <div>
            <div className="text-sm font-semibold text-zinc-100">{endpoint} — Result</div>
            <div className="text-xs text-zinc-500">
              {tsLabel}
              {durationSeconds != null && (
                <span className="ml-2 text-zinc-600">· {durationSeconds.toFixed(1)}s</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700/60 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:border-zinc-600 hover:text-zinc-200"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied!" : "Copy JSON"}
          </button>
          <button
            onClick={() => downloadJson(`${endpoint}-${timestamp}.json`, result)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700/60 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:border-zinc-600 hover:text-zinc-200"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </button>
        </div>
      </div>

      {/* Structured output */}
      <div className="p-5">
        <GeneratedOutput data={result} />
      </div>

      {/* Raw JSON toggle */}
      <div className="border-t border-zinc-800/60">
        <button
          type="button"
          onClick={() => setRawOpen((v) => !v)}
          className="flex w-full items-center justify-between px-5 py-3 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <span>Raw JSON</span>
          {rawOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
        {rawOpen && (
          <div className="border-t border-zinc-800/60 px-5 pb-5">
            <pre className="max-h-[400px] overflow-auto rounded-xl border border-zinc-800/60 bg-zinc-950/60 p-4 text-xs text-zinc-300 leading-relaxed">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
