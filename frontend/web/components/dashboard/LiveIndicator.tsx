"use client";

import { cn } from "@/lib/utils";

export function LiveIndicator({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] font-medium">
      <span className="relative inline-flex h-2 w-2">
        <span
          className={cn(
            "absolute inline-flex h-full w-full rounded-full opacity-75",
            ok ? "animate-ping bg-emerald-400" : "bg-zinc-600"
          )}
        />
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            ok ? "bg-emerald-400" : "bg-zinc-600"
          )}
        />
      </span>
      <span className={ok ? "text-emerald-400" : "text-zinc-500"}>
        {label ?? (ok ? "Live" : "Stale")}
      </span>
    </div>
  );
}
