"use client";

import { Skeleton } from "@/components/ui/skeleton";

function fmt(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

function fmtPct(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${n.toFixed(2)}%`;
}

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
  const items =
    variant === "overview"
      ? [
          { label: "Total tokens", value: fmt(cards.totalTokens) },
          { label: "Total API calls", value: fmt(cards.apiCalls) },
          { label: "Active orgs", value: fmt(cards.activeOrgs) },
          { label: "Overall cache hit rate", value: fmtPct(cards.cacheHitRatePercent) },
        ]
      : [
          { label: "Total tokens", value: fmt(cards.totalTokens) },
          { label: "Prompt tokens", value: fmt(cards.promptTokens) },
          { label: "Completion tokens", value: fmt(cards.completionTokens) },
          { label: "Total API calls", value: fmt(cards.apiCalls) },
          {
            label: "Errors",
            value:
              cards.errorCount != null
                ? `${fmt(cards.errorCount)} (${fmtPct(cards.errorRatePercent)})`
                : "—",
          },
        ];

  return (
    <div
      className={`grid grid-cols-1 gap-4 ${
        variant === "overview" ? "lg:grid-cols-4" : "lg:grid-cols-5"
      }`}
    >
      {items.map((it) => (
        <div
          key={it.label}
          className="rounded-xl border border-white/10 bg-zinc-950/40 p-4"
        >
          <div className="text-xs text-zinc-500">{it.label}</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {loading ? <Skeleton className="h-7 w-28" /> : it.value}
          </div>
        </div>
      ))}
    </div>
  );
}

