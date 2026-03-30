"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  Building2,
  Cpu,
  History,
  ListTree,
  PieChart as PieChartIcon,
  ScrollText,
  ShieldCheck,
  Timer,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  fetchAdminOrgUsage,
  fetchOrgDashboard,
  fetchUsageLogs,
  type UsageLogRow,
} from "@/lib/billingApi";

const tooltipStyle = {
  backgroundColor: "rgba(24, 24, 27, 0.96)",
  border: "1px solid rgb(63 63 70)",
  borderRadius: "8px",
  fontSize: "12px",
  color: "#e4e4e7",
};

const PIE_COLORS = ["#22d3ee", "#a78bfa"];

function fmtNum(n: number | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}

function defaultUtcMonth(): string {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function parsePeriod(s: string): string | null {
  const t = s.trim();
  if (/^\d{4}-\d{2}$/.test(t)) return t;
  return null;
}

export function OrgUsageClient({
  initialOrgId = "",
  initialPeriod = "",
}: {
  initialOrgId?: string;
  initialPeriod?: string;
}) {
  const router = useRouter();
  const fromQuery = initialOrgId.trim();
  const defaultOrg =
    fromQuery ||
    process.env.NEXT_PUBLIC_PLAYGROUND_ORG_ID?.trim() ||
    process.env.NEXT_PUBLIC_BILLING_DEFAULT_ORG?.trim() ||
    "";

  const [orgId, setOrgId] = useState(defaultOrg);
  const [periodInput, setPeriodInput] = useState(
    () => parsePeriod(initialPeriod) ?? defaultUtcMonth()
  );
  const [submittedOrg, setSubmittedOrg] = useState(defaultOrg);
  const [logsPage, setLogsPage] = useState(1);

  useEffect(() => {
    const o = initialOrgId.trim();
    if (!o) return;
    setOrgId(o);
    setSubmittedOrg(o);
    setLogsPage(1);
  }, [initialOrgId]);

  useEffect(() => {
    const p = parsePeriod(initialPeriod);
    if (p) setPeriodInput(p);
  }, [initialPeriod]);

  const period = useMemo(() => periodInput.trim(), [periodInput]);

  const adminQuery = useQuery({
    queryKey: ["admin-org-usage", period],
    queryFn: () => fetchAdminOrgUsage(period),
  });

  const dashboardQuery = useQuery({
    queryKey: ["org-dashboard", submittedOrg, period],
    queryFn: () => fetchOrgDashboard(submittedOrg, period),
    enabled: submittedOrg.length > 0,
    refetchInterval: 30_000,
  });

  const logsQuery = useQuery({
    queryKey: ["org-usage-logs", submittedOrg, period, logsPage],
    queryFn: () =>
      fetchUsageLogs(submittedOrg, { period, page: logsPage, page_size: 25 }),
    enabled: submittedOrg.length > 0,
  });

  const pushUsageUrl = (org: string, p: string) => {
    const q = new URLSearchParams();
    if (org) q.set("org", org);
    if (p) q.set("period", p);
    const qs = q.toString();
    router.push(qs ? `/usage?${qs}` : "/usage");
  };

  const onLoad = () => {
    const o = orgId.trim();
    if (!o) return;
    setSubmittedOrg(o);
    setLogsPage(1);
    pushUsageUrl(o, period);
  };

  const d = dashboardQuery.data;

  const historyChartData = useMemo(() => {
    if (!d?.history?.length) return [];
    return [...d.history]
      .sort((a, b) => String(a._id).localeCompare(String(b._id)))
      .map((row) => ({
        period: row._id,
        tokens: row.total_tokens ?? 0,
        calls: row.call_count ?? 0,
      }));
  }, [d?.history]);

  const tokenSplitData = useMemo(() => {
    if (!d?.current) return [];
    const prompt = d.current.prompt_tokens ?? 0;
    const completion = d.current.completion_tokens ?? 0;
    if (prompt <= 0 && completion <= 0) return [];
    return [
      { name: "Prompt", value: prompt },
      { name: "Completion", value: completion },
    ];
  }, [d?.current]);

  const periodDelta = useMemo(() => {
    if (!d?.history?.length || !d.period) return null;
    const sorted = [...d.history].sort((a, b) =>
      String(a._id).localeCompare(String(b._id))
    );
    const idx = sorted.findIndex((h) => h._id === d.period);
    if (idx <= 0) return null;
    const prev = sorted[idx - 1];
    const cur = sorted[idx];
    const pt = (cur.total_tokens ?? 0) - (prev.total_tokens ?? 0);
    const pct =
      (prev.total_tokens ?? 0) > 0
        ? (100 * pt) / (prev.total_tokens as number)
        : null;
    return { prevPeriod: prev._id, tokenDelta: pt, pct };
  }, [d?.history, d?.period]);

  /** Soft cap for UI gauge — set in .env to show utilization (optional). */
  const tokenBudget = useMemo(() => {
    const raw = process.env.NEXT_PUBLIC_ORG_MONTHLY_TOKEN_BUDGET?.trim();
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  }, []);

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-zinc-800/80 bg-zinc-900/25 p-5 shadow-panel">
        <h2 className="text-sm font-semibold text-zinc-200">Billing period (UTC)</h2>
        <p className="mt-1 text-xs text-zinc-500">
          Applies to the admin overview below and to any org dashboard you open. Matches{" "}
          <code className="text-zinc-400">usage_logs.billing_period</code>.
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="w-full sm:max-w-xs">
            <label className="mb-1 block text-xs text-zinc-500">Period</label>
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 font-mono text-sm"
              value={periodInput}
              onChange={(e) => setPeriodInput(e.target.value)}
              placeholder="YYYY-MM"
            />
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800/80 bg-zinc-900/25 p-5 shadow-panel">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">All organizations</h2>
            <p className="mt-1 max-w-2xl text-xs text-zinc-500">
              Aggregated from usage logs for <span className="font-mono text-zinc-400">{period}</span>.
              Click a row or <strong className="text-zinc-400">Analytics</strong> to load charts,
              limits-style utilization, and request logs for that org.
            </p>
          </div>
        </div>

        {adminQuery.isLoading && (
          <div className="mt-4 flex h-24 items-center justify-center text-sm text-zinc-500">
            Loading org list…
          </div>
        )}
        {adminQuery.isError && (
          <div className="mt-4 rounded-lg border border-red-900/50 bg-red-950/20 p-3 text-sm text-red-200">
            {adminQuery.error instanceof Error
              ? adminQuery.error.message
              : "Failed to load admin usage"}
          </div>
        )}
        {adminQuery.data && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs uppercase tracking-wide text-zinc-500">
                  <th className="py-2.5 pr-4">Org ID</th>
                  <th className="py-2.5 pr-4">Tokens</th>
                  <th className="py-2.5 pr-4">API calls</th>
                  <th className="py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {adminQuery.data.orgs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-zinc-500">
                      No usage rows for this period.
                    </td>
                  </tr>
                ) : (
                  adminQuery.data.orgs.map((row) => {
                    const active = submittedOrg === row._id;
                    return (
                      <tr
                        key={row._id}
                        className={`border-b border-zinc-800/60 transition-colors ${
                          active
                            ? "bg-cyan-950/25 ring-1 ring-inset ring-cyan-800/50"
                            : "hover:bg-zinc-900/50"
                        }`}
                      >
                        <td className="py-2.5 pr-4">
                          <button
                            type="button"
                            onClick={() => {
                              setOrgId(row._id);
                              setSubmittedOrg(row._id);
                              setLogsPage(1);
                              pushUsageUrl(row._id, period);
                            }}
                            className="font-mono text-left text-cyan-300/95 hover:underline"
                          >
                            {row._id}
                          </button>
                        </td>
                        <td className="py-2.5 pr-4 text-zinc-200">
                          {fmtNum(row.total_tokens)}
                        </td>
                        <td className="py-2.5 pr-4 text-zinc-300">
                          {fmtNum(row.call_count)}
                        </td>
                        <td className="py-2.5 text-right">
                          <Link
                            href={`/usage?${new URLSearchParams({ org: row._id, period }).toString()}`}
                            className="inline-flex items-center gap-1 rounded-lg border border-zinc-600 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:border-cyan-700 hover:text-cyan-200"
                          >
                            Analytics
                            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800/80 bg-zinc-900/25 p-5 shadow-panel">
        <h2 className="text-sm font-semibold text-zinc-200">Organization detail</h2>
        <p className="mt-1 text-xs text-zinc-500">
          Uses <code className="text-zinc-400">organization_db.organizations</code> for profile;
          billing rows in <code className="text-zinc-400">usage_logs</code>.
        </p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-zinc-500">Org ID</label>
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              placeholder="e.g. ORG001"
            />
          </div>
          <button
            type="button"
            onClick={onLoad}
            className="rounded-lg bg-cyan-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-cyan-500"
          >
            Load dashboard
          </button>
        </div>
      </section>

      {!submittedOrg && (
        <p className="text-sm text-zinc-500">
          Pick an org from the table above, enter an ID, or open a link with{" "}
          <code className="text-zinc-400">?org=…</code> then load the dashboard.
        </p>
      )}

      {dashboardQuery.isLoading && submittedOrg && (
        <div className="flex h-40 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/30">
          <span className="text-sm text-zinc-500">Loading usage…</span>
        </div>
      )}

      {dashboardQuery.isError && submittedOrg && (
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-200">
          {dashboardQuery.error instanceof Error
            ? dashboardQuery.error.message
            : "Failed to load dashboard"}
        </div>
      )}

      {d && (
        <>
          {periodDelta && (
            <section className="rounded-xl border border-zinc-800/70 bg-zinc-900/30 px-4 py-3 text-sm text-zinc-300">
              <span className="font-medium text-zinc-200">vs prior month </span>
              <span className="font-mono text-zinc-400">({periodDelta.prevPeriod})</span>
              : tokens{" "}
              <span
                className={
                  periodDelta.tokenDelta >= 0 ? "text-amber-300" : "text-emerald-300"
                }
              >
                {periodDelta.tokenDelta >= 0 ? "+" : ""}
                {fmtNum(periodDelta.tokenDelta)}
              </span>
              {periodDelta.pct != null && (
                <span className="text-zinc-500">
                  {" "}
                  ({periodDelta.pct >= 0 ? "+" : ""}
                  {periodDelta.pct.toFixed(1)}%)
                </span>
              )}
            </section>
          )}

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <StatCard
              icon={Building2}
              label="Organization"
              value={d.profile.name || d.org_id}
              sub={d.profile.orgId || d.org_id}
            />
            <StatCard
              icon={Cpu}
              label="Total tokens (period)"
              value={fmtNum(d.current.total_tokens)}
              sub={`${fmtNum(d.current.call_count)} API completions`}
            />
            <StatCard
              icon={Zap}
              label="Prompt tokens"
              value={fmtNum(d.current.prompt_tokens)}
              sub="Input side"
            />
            <StatCard
              icon={TrendingUp}
              label="Completion tokens"
              value={fmtNum(d.current.completion_tokens)}
              sub="Output side"
            />
            <StatCard
              icon={ShieldCheck}
              label="Cache hits"
              value={fmtNum(d.current.cache_hits)}
              sub={
                d.current.call_count
                  ? `${((100 * (d.current.cache_hits || 0)) / Math.max(1, d.current.call_count)).toFixed(1)}% of calls`
                  : "—"
              }
            />
            <StatCard
              icon={Timer}
              label="Avg latency"
              value={
                d.current.avg_latency_ms != null
                  ? `${Math.round(d.current.avg_latency_ms)} ms`
                  : "—"
              }
              sub={`Errors (period): ${d.errors_this_period}`}
            />
          </section>

          {tokenBudget != null && d.current.total_tokens != null && (
            <section className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-zinc-200">
                  Monthly token budget (UI)
                </p>
                <p className="text-xs text-zinc-500">
                  <code className="text-zinc-400">NEXT_PUBLIC_ORG_MONTHLY_TOKEN_BUDGET</code>
                </p>
              </div>
              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-violet-500 transition-all"
                  style={{
                    width: `${Math.min(100, (100 * (d.current.total_tokens || 0)) / tokenBudget)}%`,
                  }}
                />
              </div>
              <p className="mt-2 text-xs text-zinc-500">
                {fmtNum(d.current.total_tokens)} / {fmtNum(tokenBudget)} tokens (
                {((100 * (d.current.total_tokens || 0)) / tokenBudget).toFixed(1)}%)
              </p>
            </section>
          )}

          <section className="grid gap-6 lg:grid-cols-2">
            <Panel title="By route" subtitle={`${d.period} · token volume`} icon={ListTree}>
              {d.by_route.length === 0 ? (
                <p className="py-8 text-center text-sm text-zinc-500">No usage this period</p>
              ) : (
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={d.by_route} layout="vertical" margin={{ left: 8, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                      <XAxis type="number" tick={{ fill: "#71717a", fontSize: 10 }} />
                      <YAxis
                        type="category"
                        dataKey="_id"
                        width={140}
                        tick={{ fill: "#a1a1aa", fontSize: 10 }}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="total_tokens" fill="#22d3ee" radius={[0, 6, 6, 0]} maxBarSize={20} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>

            <Panel title="Token mix" subtitle="Prompt vs completion (period)" icon={PieChartIcon}>
              {tokenSplitData.length === 0 ? (
                <p className="py-8 text-center text-sm text-zinc-500">
                  No prompt/completion split recorded
                </p>
              ) : (
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={tokenSplitData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={56}
                        outerRadius={88}
                        paddingAngle={2}
                      >
                        {tokenSplitData.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => fmtNum(v)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <Panel title="Usage over time" subtitle="Tokens by billing period" icon={History}>
              {historyChartData.length === 0 ? (
                <p className="py-8 text-center text-sm text-zinc-500">No history yet</p>
              ) : (
                <div className="h-[280px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={historyChartData} margin={{ left: 4, right: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                      <XAxis
                        dataKey="period"
                        tick={{ fill: "#71717a", fontSize: 10 }}
                        angle={-35}
                        textAnchor="end"
                        height={64}
                      />
                      <YAxis tick={{ fill: "#71717a", fontSize: 10 }} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Line
                        type="monotone"
                        dataKey="tokens"
                        stroke="#22d3ee"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        name="Tokens"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>

            <Panel title="Monthly history" subtitle="Last periods (table)" icon={History}>
              {d.history.length === 0 ? (
                <p className="py-8 text-center text-sm text-zinc-500">No history yet</p>
              ) : (
                <div className="max-h-[280px] overflow-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-500">
                        <th className="py-2 pr-3">Period</th>
                        <th className="py-2 pr-3">Calls</th>
                        <th className="py-2">Tokens</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.history.map((row) => (
                        <tr key={row._id} className="border-b border-zinc-800/60 text-zinc-300">
                          <td className="py-2 pr-3 font-mono">{row._id}</td>
                          <td className="py-2 pr-3">{fmtNum(row.call_count)}</td>
                          <td className="py-2">{fmtNum(row.total_tokens)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </section>

          <Panel
            title="Recent usage logs"
            subtitle={`Page ${logsPage} · ${period}`}
            icon={ScrollText}
          >
            {logsQuery.isLoading ? (
              <p className="py-6 text-center text-sm text-zinc-500">Loading logs…</p>
            ) : logsQuery.isError ? (
              <p className="py-6 text-center text-sm text-red-300">
                {logsQuery.error instanceof Error ? logsQuery.error.message : "Failed"}
              </p>
            ) : (
              <>
                <div className="mb-3 flex gap-2">
                  <button
                    type="button"
                    disabled={logsPage <= 1}
                    onClick={() => setLogsPage((p) => Math.max(1, p - 1))}
                    className="rounded border border-zinc-700 px-3 py-1 text-xs text-zinc-300 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    onClick={() => setLogsPage((p) => p + 1)}
                    className="rounded border border-zinc-700 px-3 py-1 text-xs text-zinc-300"
                  >
                    Next
                  </button>
                </div>
                <LogsTable rows={logsQuery.data?.logs ?? []} />
              </>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 shadow-sm">
      <div className="flex items-center gap-2 text-zinc-500">
        <Icon className="h-4 w-4 text-console-accent" strokeWidth={1.75} />
        <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-2 text-lg font-semibold tracking-tight text-zinc-50">{value}</p>
      {sub && <p className="mt-1 text-xs text-zinc-500">{sub}</p>}
    </div>
  );
}

function Panel({
  title,
  subtitle,
  icon: Icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/40 shadow-panel">
      <div className="border-b border-zinc-800/60 px-4 py-3">
        <div className="flex items-center gap-2">
          {Icon ? (
            <Icon className="h-4 w-4 shrink-0 text-console-accent" strokeWidth={1.75} />
          ) : null}
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
            {subtitle && <p className="text-[11px] text-zinc-500">{subtitle}</p>}
          </div>
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function LogsTable({ rows }: { rows: UsageLogRow[] }) {
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-zinc-500">No log rows</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-left text-[11px]">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500">
            <th className="py-2 pr-2">Time (UTC)</th>
            <th className="py-2 pr-2">Route</th>
            <th className="py-2 pr-2">Status</th>
            <th className="py-2 pr-2">Tokens</th>
            <th className="py-2 pr-2">Cache</th>
            <th className="py-2 pr-2">Latency</th>
            <th className="py-2 pr-2">Model</th>
            <th className="py-2">Correlation</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.request_id ? `${r.request_id}-${i}` : `log-${i}`}
              className="border-b border-zinc-800/50 text-zinc-300"
            >
              <td className="py-2 pr-2 font-mono text-zinc-400">
                {r.created_at
                  ? String(r.created_at).slice(0, 19).replace("T", " ")
                  : "—"}
              </td>
              <td className="py-2 pr-2">{r.route ?? "—"}</td>
              <td className="py-2 pr-2">
                <span
                  className={
                    r.status === "error"
                      ? "text-red-400"
                      : r.status === "success"
                        ? "text-emerald-400"
                        : ""
                  }
                >
                  {r.status ?? "—"}
                </span>
              </td>
              <td className="py-2 pr-2 font-mono">{fmtNum(r.total_tokens)}</td>
              <td className="py-2 pr-2">{r.cache_hit ? "yes" : "no"}</td>
              <td className="py-2 pr-2">{r.latency_ms != null ? `${r.latency_ms} ms` : "—"}</td>
              <td className="py-2 pr-2 max-w-[120px] truncate" title={r.model_name}>
                {r.model_name ?? "—"}
              </td>
              <td className="py-2 font-mono text-zinc-500 max-w-[140px] truncate" title={r.correlation_id}>
                {r.correlation_id || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.some((r) => r.error_detail) && (
        <p className="mt-3 text-[10px] text-zinc-600">
          Expand errors in Mongo or add a detail view; <code>error_detail</code> is stored on
          failed rows.
        </p>
      )}
    </div>
  );
}
