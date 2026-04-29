"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { OrgSummaryCards } from "@/components/usage/OrgSummaryCards";
import { PeriodSelector } from "@/components/usage/PeriodSelector";
import { currentUtcMonth, isValidPeriod } from "@/components/usage/periodUtils";
import { OrgsTable, type OrgUsageRow } from "@/components/usage/OrgsTable";
import { useAdminUsageQuery, useOrgDashboardQuery } from "@/hooks/useBilling";
import type { OrgDashboardResponse } from "@/types/api";

// ── Per-org enrichment hook ───────────────────────────────────────────────────
// Fetches the full dashboard for each org in parallel so we can show
// prompt_tokens, completion_tokens, cache_hit_rate_percent, avg_latency_ms,
// errors, and last_active — fields that /admin/usage doesn't return.
function useEnrichedOrgRows(
  baseRows: Array<{ org_id: string; total_tokens: number | null; call_count: number | null }>,
  period: string
): { rows: OrgUsageRow[]; enriching: boolean } {
  // We call the hook for up to 20 orgs. React rules require a fixed number of
  // hook calls, so we pad to a fixed size and use `enabled` to skip extras.
  const MAX = 20;
  const padded = useMemo(() => {
    const arr = baseRows.slice(0, MAX);
    while (arr.length < MAX) arr.push({ org_id: "", total_tokens: null, call_count: null });
    return arr;
  }, [baseRows]);

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q0 = useOrgDashboardQuery(padded[0].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q1 = useOrgDashboardQuery(padded[1].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q2 = useOrgDashboardQuery(padded[2].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q3 = useOrgDashboardQuery(padded[3].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q4 = useOrgDashboardQuery(padded[4].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q5 = useOrgDashboardQuery(padded[5].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q6 = useOrgDashboardQuery(padded[6].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q7 = useOrgDashboardQuery(padded[7].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q8 = useOrgDashboardQuery(padded[8].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q9 = useOrgDashboardQuery(padded[9].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q10 = useOrgDashboardQuery(padded[10].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q11 = useOrgDashboardQuery(padded[11].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q12 = useOrgDashboardQuery(padded[12].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q13 = useOrgDashboardQuery(padded[13].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q14 = useOrgDashboardQuery(padded[14].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q15 = useOrgDashboardQuery(padded[15].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q16 = useOrgDashboardQuery(padded[16].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q17 = useOrgDashboardQuery(padded[17].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q18 = useOrgDashboardQuery(padded[18].org_id, period);
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const q19 = useOrgDashboardQuery(padded[19].org_id, period);

  const queries = [q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19];

  const enriching = queries.some((q) => q.isLoading);

  const rows = useMemo(() => {
    return baseRows.map((base, i) => {
      const d = queries[i]?.data as OrgDashboardResponse | undefined;
      const cur = d?.current;
      const profile = d?.profile as Record<string, unknown> | undefined;

      // Derive last_active from history
      const history = (d as any)?.history as Array<{ _id: string }> | undefined;
      const lastActive = history?.length
        ? [...history].sort((a, b) => String(b._id).localeCompare(String(a._id)))[0]._id
        : null;

      // Cache hit rate: compute from hits/calls if not directly available
      const cacheHits = cur?.cache_hits ?? null;
      const callCount = cur?.call_count ?? base.call_count ?? null;
      const cacheHitRate =
        typeof cacheHits === "number" && typeof callCount === "number" && callCount > 0
          ? (100 * cacheHits) / callCount
          : null;

      return {
        org_id: base.org_id,
        org_name:
          (profile?.name as string | undefined) ??
          cur?.org_name ??
          null,
        total_tokens: cur?.total_tokens ?? base.total_tokens ?? null,
        prompt_tokens: cur?.prompt_tokens ?? null,
        completion_tokens: cur?.completion_tokens ?? null,
        call_count: cur?.call_count ?? base.call_count ?? null,
        cache_hit_rate_percent: cacheHitRate,
        cache_hits: cacheHits,
        avg_latency_ms: cur?.avg_latency_ms ?? null,
        errors: cur?.errors ?? (d as any)?.errors_this_period ?? null,
        last_active: lastActive,
      } satisfies OrgUsageRow;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseRows, ...queries.map((q) => q.data)]);

  return { rows, enriching };
}

// ── Main component ────────────────────────────────────────────────────────────
export function UsageOverviewClient({ initialPeriod }: { initialPeriod: string }) {
  const router = useRouter();
  const [period, setPeriod] = useState(() =>
    isValidPeriod(initialPeriod) ? initialPeriod : currentUtcMonth()
  );

  const query = useAdminUsageQuery(period);

  // Base rows from admin/usage (only has _id, total_tokens, call_count)
  const baseRows = useMemo(() => {
    const orgs = Array.isArray((query.data as any)?.orgs) ? (query.data as any).orgs : [];
    return orgs.map((r: any) => ({
      org_id: String(r._id ?? r.org_id ?? ""),
      total_tokens: r.total_tokens ?? null,
      call_count: r.call_count ?? null,
    }));
  }, [query.data]);

  // Enrich with per-org dashboard data
  const { rows, enriching } = useEnrichedOrgRows(baseRows, period);

  const totals = useMemo(() => {
    const totalTokens = rows.reduce((a, r) => a + (r.total_tokens ?? 0), 0);
    const totalCalls = rows.reduce((a, r) => a + (r.call_count ?? 0), 0);
    const activeOrgs = rows.filter((r) => (r.call_count ?? 0) > 0).length;
    const withRate = rows.filter((r) => r.cache_hit_rate_percent != null);
    const weightedCache = (() => {
      if (withRate.length === 0) return null;
      let num = 0, den = 0;
      for (const r of withRate) {
        const w = r.call_count ?? 1;
        num += (r.cache_hit_rate_percent ?? 0) * w;
        den += w;
      }
      return den > 0 ? num / den : null;
    })();
    return { totalTokens, totalCalls, activeOrgs, weightedCache };
  }, [rows]);

  const billingUnavailable =
    query.isError &&
    query.error instanceof Error &&
    query.error.message.includes("503");

  const onPeriodChange = (p: string) => {
    setPeriod(p);
    router.push(`/usage?${new URLSearchParams({ period: p }).toString()}`);
  };

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-2xl font-bold text-zinc-50">Usage & Billing</div>
          <div className="mt-1 text-sm text-zinc-500">
            Period: <span className="font-mono text-zinc-300">{period}</span>
            {enriching && (
              <span className="ml-3 text-[11px] text-zinc-600 animate-pulse">
                Loading org details…
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodSelector value={period} onChange={onPeriodChange} monthsBack={12} />
          <Button
            variant="outline"
            className="border-zinc-700 hover:border-zinc-600"
            onClick={() => query.refetch()}
          >
            Refresh
          </Button>
        </div>
      </div>

      {billingUnavailable && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          Billing database unavailable. Showing cached data if available.
        </div>
      )}

      {/* Summary cards */}
      <OrgSummaryCards
        variant="overview"
        loading={query.isLoading}
        cards={{
          totalTokens: totals.totalTokens,
          apiCalls: totals.totalCalls,
          activeOrgs: totals.activeOrgs,
          cacheHitRatePercent: totals.weightedCache,
        }}
      />

      {query.isError && !billingUnavailable && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300">
          {query.error instanceof Error ? query.error.message : "Failed to load usage"}
        </div>
      )}

      {/* Orgs table — enriched */}
      <OrgsTable rows={rows} period={period} loading={query.isLoading} />
    </div>
  );
}
