"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = {
  route: string;
  call_count?: number | null;
  total_tokens?: number | null;
  avg_latency_ms?: number | null;
};

const tooltipStyle = {
  backgroundColor: "rgba(9, 9, 11, 0.92)",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "10px",
  fontSize: "12px",
  color: "rgba(255,255,255,0.86)",
};

function fmtNum(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString();
}

export function ByRouteChart({
  rows,
  totalTokens,
}: {
  rows: Row[];
  totalTokens: number;
}) {
  const sorted = useMemo(() => {
    return [...rows]
      .sort((a, b) => (b.total_tokens ?? 0) - (a.total_tokens ?? 0))
      .map((r) => ({
        route: r.route,
        call_count: r.call_count ?? 0,
        total_tokens: r.total_tokens ?? 0,
        avg_latency_ms: r.avg_latency_ms ?? null,
        pct_total: totalTokens > 0 ? (100 * (r.total_tokens ?? 0)) / totalTokens : 0,
      }));
  }, [rows, totalTokens]);

  if (sorted.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">By-route breakdown</div>
        <div className="mt-2 text-sm text-zinc-500">No usage this period.</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="text-sm text-zinc-200">By-route breakdown</div>

      <div className="mt-3 h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" horizontal={false} />
            <XAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} type="number" />
            <YAxis
              type="category"
              dataKey="route"
              width={220}
              tick={{ fill: "rgba(255,255,255,0.65)", fontSize: 11 }}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="total_tokens" fill="#22d3ee" radius={[0, 6, 6, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 overflow-auto">
        <table className="min-w-[820px] w-full text-left text-sm">
          <thead className="text-xs text-zinc-500">
            <tr className="border-b border-white/10">
              <th className="py-2 pr-3">Route</th>
              <th className="py-2 pr-3">Calls</th>
              <th className="py-2 pr-3">Total Tokens</th>
              <th className="py-2 pr-3">Avg Latency ms</th>
              <th className="py-2">% of Total</th>
            </tr>
          </thead>
          <tbody className="text-zinc-200">
            {sorted.map((r) => (
              <tr key={r.route} className="border-b border-white/5">
                <td className="py-2 pr-3 font-mono text-[12px] text-zinc-300">{r.route}</td>
                <td className="py-2 pr-3 tabular-nums">{fmtNum(r.call_count)}</td>
                <td className="py-2 pr-3 tabular-nums">{fmtNum(r.total_tokens)}</td>
                <td className="py-2 pr-3 tabular-nums">
                  {r.avg_latency_ms == null ? "—" : Math.round(r.avg_latency_ms)}
                </td>
                <td className="py-2 tabular-nums">{r.pct_total.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

