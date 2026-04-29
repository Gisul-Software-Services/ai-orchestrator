"use client";

import { format } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type QueueHistoryPoint = {
  timestamp: number;
  [queueName: string]: number;
};

const PALETTE = [
  { line: "#22d3ee", fill: "rgba(34,211,238,0.15)" },
  { line: "#a78bfa", fill: "rgba(167,139,250,0.15)" },
  { line: "#34d399", fill: "rgba(52,211,153,0.15)" },
  { line: "#fbbf24", fill: "rgba(251,191,36,0.15)" },
  { line: "#f87171", fill: "rgba(248,113,113,0.15)" },
  { line: "#38bdf8", fill: "rgba(56,189,248,0.15)" },
  { line: "#e879f9", fill: "rgba(232,121,249,0.15)" },
  { line: "#f97316", fill: "rgba(249,115,22,0.15)" },
];

export function QueueChart({
  data,
  height = 260,
}: {
  data: QueueHistoryPoint[];
  height?: number;
}) {
  const keys = Object.keys(data.at(-1) ?? {}).filter((k) => k !== "timestamp");

  if (keys.length === 0) {
    return (
      <div className="flex h-[180px] items-center justify-center rounded-xl border border-zinc-800/60 bg-zinc-900/50 text-sm text-zinc-600">
        No queue history yet — collecting samples…
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm">
      <div className="mb-1 text-sm font-semibold text-zinc-100">Queue depths over time</div>
      <div className="mb-3 text-xs text-zinc-600">Per-queue depth — rolling 5 min</div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ left: 4, right: 10, top: 8, bottom: 0 }}>
            <defs>
              {keys.map((k, idx) => {
                const p = PALETTE[idx % PALETTE.length];
                return (
                  <linearGradient key={k} id={`qgrad-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={p.line} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={p.line} stopOpacity={0} />
                  </linearGradient>
                );
              })}
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="timestamp"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(ts) => format(new Date(ts), "HH:mm")}
              tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              interval={9}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={28}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(9,9,11,0.95)",
                border: "1px solid rgba(63,63,70,0.8)",
                borderRadius: 10,
                fontSize: 12,
                color: "#fafafa",
                backdropFilter: "blur(12px)",
              }}
              labelFormatter={(ts) => format(new Date(Number(ts)), "HH:mm:ss")}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8, color: "rgba(255,255,255,0.5)" }}
            />
            {keys.map((k, idx) => {
              const p = PALETTE[idx % PALETTE.length];
              return (
                <Area
                  key={k}
                  type="monotone"
                  dataKey={k}
                  stroke={p.line}
                  strokeWidth={2}
                  fill={`url(#qgrad-${k})`}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
