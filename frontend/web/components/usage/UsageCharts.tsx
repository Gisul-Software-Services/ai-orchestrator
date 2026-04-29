"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = { period: string; total_tokens: number; call_count: number };

const tooltipStyle = {
  backgroundColor: "rgba(9, 9, 11, 0.95)",
  border: "1px solid rgba(63,63,70,0.8)",
  borderRadius: "10px",
  fontSize: "12px",
  color: "#fafafa",
  backdropFilter: "blur(12px)",
};

export function UsageCharts({ history }: { history: Point[] }) {
  if (history.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {["Token usage over time", "Calls over time"].map((title) => (
          <div key={title} className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4">
            <div className="text-sm font-semibold text-zinc-100">{title}</div>
            <div className="mt-3 flex h-[200px] items-center justify-center text-sm text-zinc-600">
              No history data
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
        <div className="mb-1 text-sm font-semibold text-zinc-100">Token usage over time</div>
        <div className="text-2xl font-bold tabular-nums text-console-accent">
          {history.at(-1)?.total_tokens?.toLocaleString() ?? "—"}
        </div>
        <div className="mt-3 h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ left: 4, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                type="monotone"
                dataKey="total_tokens"
                stroke="#22d3ee"
                strokeWidth={2}
                fill="url(#tokenGrad)"
                dot={false}
                isAnimationActive={false}
                name="Tokens"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
        <div className="mb-1 text-sm font-semibold text-zinc-100">API calls over time</div>
        <div className="text-2xl font-bold tabular-nums text-console-emerald">
          {history.at(-1)?.call_count?.toLocaleString() ?? "—"}
        </div>
        <div className="mt-3 h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ left: 4, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="callGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                type="monotone"
                dataKey="call_count"
                stroke="#34d399"
                strokeWidth={2}
                fill="url(#callGrad)"
                dot={false}
                isAnimationActive={false}
                name="Calls"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
