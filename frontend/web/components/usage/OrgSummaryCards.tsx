"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function fmt(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

function fmtPct(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function fmtMs(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${Math.round(n)} ms`;
}

type CardItem = {
  label: string;
  value: string;
  accent?: "cyan" | "violet" | "emerald" | "red" | "amber";
};

export function OrgSummaryCards({
  variant,
  loading,
  cards,
}: {
  variant: "overview" | "detail";
  loading: boolean;
  cards: {
    totalTokens?: number | null;
    promptTokens?: number | null;
    completionTokens?: number | null;
    apiCalls?: number | null;
    activeOrgs?: number | null;
    cacheHitRatePercent?: number | null;
    avgLatencyMs?: number | null;
    errorCount?: number | null;
    errorRatePercent?: number | null;
  };
}) {
  const items: CardItem[] =
    variant === "overview"
      ? [
          { label: "Total tokens", value: fmt(cards.totalTokens), accent: "cyan" },
          { label: "Total API calls", value: fmt(cards.apiCalls), accent: "violet" },
          { label: "Active orgs", value: fmt(cards.activeOrgs), accent: "emerald" },
          {
            label: "Overall cache hit rate",
            value: fmtPct(cards.cacheHitRatePercent),
            accent: cards.cacheHitRatePercent != null && cards.cacheHitRatePercent > 50
              ? "emerald"
              : "amber",
          },
        ]
      : [
          { label: "Total tokens", value: fmt(cards.totalTokens), accent: "cyan" },
          { label: "Prompt tokens", value: fmt(cards.promptTokens), accent: "violet" },
          { label: "Completion tokens", value: fmt(cards.completionTokens), accent: "violet" },
          { label: "Total API calls", value: fmt(cards.apiCalls), accent: "emerald" },
          {
            label: "Errors",
            value:
              cards.errorCount != null
                ? `${fmt(cards.errorCount)} (${fmtPct(cards.errorRatePercent)})`
                : "—",
            accent: (cards.errorCount ?? 0) > 0 ? "red" : "emerald",
          },
        ];

  const accentBorder: Record<string, string> = {
    cyan: "border-cyan-500/20",
    violet: "border-violet-500/20",
    emerald: "border-emerald-500/20",
    red: "border-red-500/20",
    amber: "border-amber-500/20",
  };
  const accentText: Record<string, string> = {
    cyan: "text-console-accent",
    violet: "text-console-violet",
    emerald: "text-console-emerald",
    red: "text-red-400",
    amber: "text-amber-400",
  };

  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-3",
        variant === "overview" ? "lg:grid-cols-4" : "lg:grid-cols-5"
      )}
    >
      {items.map((it) => (
        <div
          key={it.label}
          className={cn(
            "relative overflow-hidden rounded-xl border bg-zinc-900/60 p-4 backdrop-blur-sm",
            it.accent ? accentBorder[it.accent] : "border-zinc-800/60"
          )}
        >
          {/* Top gradient line */}
          {it.accent && (
            <div
              className={cn(
                "absolute inset-x-0 top-0 h-px opacity-50",
                it.accent === "cyan" && "bg-gradient-to-r from-transparent via-cyan-500/60 to-transparent",
                it.accent === "violet" && "bg-gradient-to-r from-transparent via-violet-500/60 to-transparent",
                it.accent === "emerald" && "bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent",
                it.accent === "red" && "bg-gradient-to-r from-transparent via-red-500/60 to-transparent",
                it.accent === "amber" && "bg-gradient-to-r from-transparent via-amber-500/60 to-transparent",
              )}
            />
          )}
          <div className="text-xs font-medium text-zinc-500">{it.label}</div>
          <div
            className={cn(
              "mt-2 text-2xl font-bold tabular-nums",
              it.accent ? accentText[it.accent] : "text-zinc-100"
            )}
          >
            {loading ? <Skeleton className="h-7 w-28" /> : it.value}
          </div>
        </div>
      ))}
    </div>
  );
}
