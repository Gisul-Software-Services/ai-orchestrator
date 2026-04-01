"use client";

import { ResponsiveContainer, LineChart, Line, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";

type Point = { period: string; total_tokens: number; call_count: number };

const tooltipStyle = {
  backgroundColor: "rgba(9, 9, 11, 0.92)",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "10px",
  fontSize: "12px",
  color: "rgba(255,255,255,0.86)",
};

export function UsageCharts({ history }: { history: Point[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">Token usage over time</div>
        <div className="mt-3 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ left: 8, right: 16, top: 8, bottom: 12 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="total_tokens" stroke="#22d3ee" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">Calls over time</div>
        <div className="mt-3 h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ left: 8, right: 16, top: 8, bottom: 12 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="call_count" stroke="#22c55e" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

