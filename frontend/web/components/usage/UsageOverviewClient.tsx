"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { OrgSummaryCards } from "@/components/usage/OrgSummaryCards";
import { PeriodSelector } from "@/components/usage/PeriodSelector";
import { currentUtcMonth, isValidPeriod } from "@/components/usage/periodUtils";
import { OrgsTable, type OrgUsageRow } from "@/components/usage/OrgsTable";
import { useAdminUsageQuery } from "@/hooks/useBilling";

function toOrgRows(resp: any): OrgUsageRow[] {
  const orgs = Array.isArray(resp?.orgs) ? resp.orgs : [];
  return orgs.map((r: any) => ({
    org_id: String(r._id ?? r.org_id ?? ""),
    org_name: r.org_name ?? r.orgName ?? r.name ?? null,
    total_tokens: r.total_tokens ?? null,
    prompt_tokens: r.prompt_tokens ?? null,
    completion_tokens: r.completion_tokens ?? null,
    call_count: r.call_count ?? null,
    cache_hit_rate_percent: r.cache_hit_rate_percent ?? r.cache_hit_rate ?? null,
    cache_hits: r.cache_hits ?? null,
    avg_latency_ms: r.avg_latency_ms ?? null,
    errors: r.errors ?? null,
    last_active: r.last_active ?? r.last_active_at ?? null,
  }));
}

export function UsageOverviewClient({ initialPeriod }: { initialPeriod: string }) {
  const router = useRouter();
  const [period, setPeriod] = useState(() =>
    isValidPeriod(initialPeriod) ? initialPeriod : currentUtcMonth()
  );

  const query = useAdminUsageQuery(period);
  const rows = useMemo(
    () => (query.data ? toOrgRows(query.data as any) : []),
    [query.data]
  );

  const totals = useMemo(() => {
    const totalTokens = rows.reduce((a, r) => a + (r.total_tokens ?? 0), 0);
    const totalCalls = rows.reduce((a, r) => a + (r.call_count ?? 0), 0);
    const activeOrgs = rows.filter((r) => (r.call_count ?? 0) > 0).length;
    const weightedCache = (() => {
      const withRate = rows.filter(
        (r) => (r.cache_hit_rate_percent ?? null) != null
      );
      if (withRate.length === 0) return null;
      let num = 0;
      let den = 0;
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
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-2xl font-semibold">Usage & Billing</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodSelector value={period} onChange={onPeriodChange} monthsBack={12} />
          <Button
            variant="outline"
            className="border-white/10"
            onClick={() => query.refetch()}
          >
            Refresh
          </Button>
        </div>
      </div>

      {billingUnavailable ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Billing database unavailable. Showing cached data if available.
        </div>
      ) : null}

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

      {query.isError && !billingUnavailable ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {query.error instanceof Error ? query.error.message : "Failed to load usage"}
        </div>
      ) : null}

      <OrgsTable rows={rows} period={period} loading={query.isLoading} />
    </div>
  );
}

