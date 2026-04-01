"use client";

import { Button } from "@/components/ui/button";

export function ConfigRow({
  label,
  value,
  copyable = false,
}: {
  label: string;
  value: string;
  copyable?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-white/5 py-2">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="flex items-center gap-2">
        <div className="max-w-[560px] break-all text-right text-sm text-zinc-200">
          {value}
        </div>
        {copyable ? (
          <Button
            variant="outline"
            size="sm"
            className="border-white/10"
            onClick={() => navigator.clipboard.writeText(value)}
          >
            Copy
          </Button>
        ) : null}
      </div>
    </div>
  );
}

