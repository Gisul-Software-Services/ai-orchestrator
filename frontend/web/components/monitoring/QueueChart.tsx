"use client";

import { format } from "date-fns";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type QueueHistoryPoint = {
  timestamp: number;
  [queueName: string]: number;
};

const COLORS = [
  "#22c55e",
  "#38bdf8",
  "#a78bfa",
  "#f59e0b",
  "#ef4444",
  "#14b8a6",
  "#e879f9",
  "#f97316",
  "#60a5fa",
  "#84cc16",
];

export function QueueChart({
  data,
  height = 240,
}: {
  data: QueueHistoryPoint[];
  height?: number;
}) {
  const keys = Object.keys(data.at(-1) ?? {}).filter((k) => k !== "timestamp");

  if (keys.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
        <div className="text-sm text-zinc-200">Queue Depths</div>
        <div className="mt-2 text-sm text-zinc-500">No queue data yet.</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="text-sm text-zinc-200">Queue Depths (by endpoint)</div>
      <div className="mt-3" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: 4, right: 10, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis
              dataKey="timestamp"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(ts) => format(new Date(ts), "HH:mm:ss")}
              tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }}
              axisLine={{ stroke: "rgba(255,255,255,0.10)" }}
              tickLine={{ stroke: "rgba(255,255,255,0.10)" }}
              interval={9}
            />
            <YAxis
              tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }}
              axisLine={{ stroke: "rgba(255,255,255,0.10)" }}
              tickLine={{ stroke: "rgba(255,255,255,0.10)" }}
              width={36}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(9,9,11,0.92)",
                border: "1px solid rgba(255,255,255,0.10)",
                borderRadius: 10,
                color: "rgba(255,255,255,0.86)",
              }}
              labelFormatter={(ts) => format(new Date(Number(ts)), "HH:mm:ss")}
            />
            <Legend
              wrapperStyle={{ color: "rgba(255,255,255,0.65)", fontSize: 11 }}
            />
            {keys.map((k, idx) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                dot={false}
                stroke={COLORS[idx % COLORS.length]}
                strokeWidth={2}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

