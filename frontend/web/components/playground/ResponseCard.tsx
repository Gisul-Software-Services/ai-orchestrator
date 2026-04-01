"use client";

import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { GeneratedOutput } from "@/components/playground/generated/GeneratedOutput";

function downloadJson(filename: string, obj: unknown) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], {
    type: "application/json",
  });
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
}: {
  endpoint: string;
  result: unknown;
  timestamp: number;
}) {
  const tsLabel = useMemo(
    () => new Date(timestamp).toLocaleString(),
    [timestamp]
  );

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-zinc-50">{endpoint}</div>
          <div className="text-xs text-zinc-400">{tsLabel}</div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
            }}
          >
            Copy JSON
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadJson(`${endpoint}-${timestamp}.json`, result)}
          >
            Download
          </Button>
        </div>
      </div>

      {/* Structured rendering (reuses existing per-endpoint views) */}
      <GeneratedOutput data={result} />
    </div>
  );
}

