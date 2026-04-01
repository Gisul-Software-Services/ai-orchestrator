"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { PeriodSelector } from "@/components/usage/PeriodSelector";
import { currentUtcMonth, isValidPeriod } from "@/components/usage/periodUtils";
import { OrgSummaryCards } from "@/components/usage/OrgSummaryCards";
import { UsageCharts } from "@/components/usage/UsageCharts";
import { ByRouteChart } from "@/components/usage/ByRouteChart";
import { LogsTable } from "@/components/usage/LogsTable";
import { useOrgDashboardQuery, useOrgLogsQuery } from "@/hooks/useBilling";

function asArray<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

export function UsageOrgDetailClient({
  orgId,
  initialPeriod,
}: {
  orgId: string;
  initialPeriod: string;
}) {
  const router = useRouter();
  const [period, setPeriod] = useState(() =>
    isValidPeriod(initialPeriod) ? initialPeriod : currentUtcMonth()
  );

  const [page, setPage] = useState(1);
  const [routeFilter, setRouteFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "success" | "error">(
    "all"
  );

  const dashboardQuery = useOrgDashboardQuery(orgId, period);
  const logsQuery = useOrgLogsQuery(orgId, period, page, 20, routeFilter, statusFilter);

  const billingUnavailable =
    (dashboardQuery.isError &&
      dashboardQuery.error instanceof Error &&
      dashboardQuery.error.message.includes("503")) ||
    (logsQuery.isError &&
      logsQuery.error instanceof Error &&
      logsQuery.error.message.includes("503"));

  const d = dashboardQuery.data as any;
  const orgName = d?.profile?.name ?? d?.current?.org_name ?? null;

  const summary = useMemo(() => {
    const cur = d?.current ?? {};
    const total = Number(cur.total_tokens ?? 0) || 0;
    const calls = Number(cur.call_count ?? 0) || 0;
    const errors = Number(cur.errors ?? d?.errors_this_period ?? 0) || 0;
    const errorRatePercent = calls > 0 ? (100 * errors) / calls : null;
    return {
      totalTokens: cur.total_tokens ?? null,
      promptTokens: cur.prompt_tokens ?? null,
      completionTokens: cur.completion_tokens ?? null,
      apiCalls: cur.call_count ?? null,
      errorCount: errors,
      errorRatePercent,
      totalTokensNum: total,
    };
  }, [d]);

  const history = useMemo(() => {
    const h = asArray<any>(d?.history);
    return [...h]
      .sort((a, b) => String(a._id).localeCompare(String(b._id)))
      .map((r) => ({
        period: String(r._id),
        total_tokens: Number(r.total_tokens ?? 0) || 0,
        call_count: Number(r.call_count ?? 0) || 0,
      }));
  }, [d?.history]);

  const byRoute = useMemo(() => {
    const r = asArray<any>(d?.by_route);
    return r.map((x) => ({
      route: String(x._id ?? x.route ?? ""),
      call_count: x.call_count ?? null,
      total_tokens: x.total_tokens ?? null,
      avg_latency_ms: x.avg_latency_ms ?? null,
    }));
  }, [d?.by_route]);

  const allRoutes = useMemo(
    () =>
      Array.from(
        new Set(byRoute.map((r) => r.route).filter((r) => r && r !== ""))
      ).sort((a, b) => a.localeCompare(b)),
    [byRoute]
  );

  const onPeriodChange = (p: string) => {
    setPeriod(p);
    setPage(1);
    router.push(
      `/usage/${encodeURIComponent(orgId)}?${new URLSearchParams({ period: p }).toString()}`
    );
  };

  const orgNotFound =
    dashboardQuery.isError &&
    dashboardQuery.error instanceof Error &&
    (dashboardQuery.error.message.includes("404") ||
      dashboardQuery.error.message.toLowerCase().includes("not found"));

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-start gap-3">
          <Button asChild variant="outline" className="border-white/10">
            <Link href={`/usage?${new URLSearchParams({ period }).toString()}`}>
              Back
            </Link>
          </Button>
          <div>
            <div className="text-2xl font-semibold">
              {orgId}
              {orgName ? (
                <span className="ml-2 font-normal text-zinc-400">— {orgName}</span>
              ) : null}
            </div>
            <div className="mt-1 text-sm text-zinc-400">Usage & Billing</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <PeriodSelector value={period} onChange={onPeriodChange} monthsBack={12} />
          <Button
            variant="outline"
            className="border-white/10"
            onClick={() => {
              dashboardQuery.refetch();
              logsQuery.refetch();
            }}
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

      {orgNotFound ? (
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-6">
          <div className="text-lg font-semibold">Organisation {orgId} not found</div>
          <div className="mt-2 text-sm text-zinc-500">
            Check the org id and try again.
          </div>
          <div className="mt-4">
            <Button asChild variant="outline" className="border-white/10">
              <Link href="/usage">Back to overview</Link>
            </Button>
          </div>
        </div>
      ) : (
        <>
          <OrgSummaryCards
            variant="detail"
            loading={dashboardQuery.isLoading}
            cards={{
              totalTokens: summary.totalTokens,
              promptTokens: summary.promptTokens,
              completionTokens: summary.completionTokens,
              apiCalls: summary.apiCalls,
              errorCount: summary.errorCount,
              errorRatePercent: summary.errorRatePercent,
            }}
          />

          <UsageCharts history={history} />

          <ByRouteChart rows={byRoute} totalTokens={summary.totalTokensNum} />

          <LogsTable
            orgId={orgId}
            period={period}
            rows={(logsQuery.data?.logs ?? []) as any}
            loading={logsQuery.isLoading}
            error={
              logsQuery.isError
                ? logsQuery.error instanceof Error
                  ? logsQuery.error.message
                  : "Failed to load logs"
                : null
            }
            page={page}
            pageSize={20}
            onPageChange={setPage}
            routeFilter={routeFilter}
            statusFilter={statusFilter}
            onRouteFilterChange={(v) => {
              setRouteFilter(v);
              setPage(1);
            }}
            onStatusFilterChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            allRoutes={allRoutes}
          />
        </>
      )}
    </div>
  );
}

