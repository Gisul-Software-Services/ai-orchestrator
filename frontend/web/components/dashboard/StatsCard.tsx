"use client";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export function StatsCard({
  title,
  value,
  subtitle,
  indicatorColor,
  loading,
}: {
  title: string;
  value?: string;
  subtitle?: string;
  indicatorColor?: "emerald" | "red" | "amber" | "cyan" | "zinc";
  loading?: boolean;
}) {
  const dot =
    indicatorColor === "emerald"
      ? "bg-emerald-400"
      : indicatorColor === "red"
        ? "bg-red-400"
        : indicatorColor === "amber"
          ? "bg-amber-400"
          : indicatorColor === "cyan"
            ? "bg-cyan-400"
            : "bg-zinc-500";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-medium text-zinc-400">{title}</div>
        <span className={cn("h-2 w-2 rounded-full", dot)} />
      </div>
      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-3 w-28" />
        </div>
      ) : (
        <>
          <div className="text-2xl font-semibold tracking-tight text-zinc-50">
            {value ?? "—"}
          </div>
          {subtitle ? (
            <div className="mt-1 text-xs text-zinc-400">{subtitle}</div>
          ) : null}
        </>
      )}
    </div>
  );
}

