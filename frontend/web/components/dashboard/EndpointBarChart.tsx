"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = [
  "#22d3ee", // cyan
  "#a78bfa", // violet
  "#34d399", // emerald
  "#fbbf24", // amber
  "#f87171", // red
  "#60a5fa", // blue
  "#e879f9", // pink
  "#4ade80", // green
  "#fb923c", // orange
];

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-zinc-700/80 bg-zinc-900/95 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
      <div className="mb-1 font-mono text-zinc-400">{label}</div>
      <div className="font-bold text-zinc-100">
        {payload[0]?.value?.toLocaleString()} requests
      </div>
    </div>
  );
}

export function EndpointBarChart({
  data,
  height = 260,
}: {
  data: { endpoint: string; value: number }[];
  height?: number;
}) {
  if (data.length === 0) return null;

  const cleaned = data.map((d) => ({
    ...d,
    endpoint: d.endpoint
      .replace("/api/v1/generate-", "")
      .replace("/api/v1/", "")
      .replace("generate-", ""),
  }));

  const maxVal = Math.max(...cleaned.map((d) => d.value));
  // Add 20% padding to the right so bars don't fill 100% of width
  const xDomainMax = Math.ceil(maxVal * 1.25) || 1;

  // Dynamic bar size — smaller when many endpoints
  const barSize = Math.max(10, Math.min(22, Math.floor(260 / cleaned.length)));
  // Dynamic left margin based on longest label
  const longestLabel = Math.max(...cleaned.map((d) => d.endpoint.length));
  const leftMargin = Math.min(140, Math.max(80, longestLabel * 7));

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={cleaned}
          layout="vertical"
          margin={{ top: 4, right: 60, bottom: 4, left: leftMargin }}
          barCategoryGap="30%"
        >
          <XAxis
            type="number"
            domain={[0, xDomainMax]}
            tick={{ fill: "#52525b", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v.toLocaleString()}
          />
          <YAxis
            type="category"
            dataKey="endpoint"
            tick={{ fill: "#a1a1aa", fontSize: 11, fontFamily: "monospace" }}
            width={leftMargin}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={barSize}
            label={{
              position: "right",
              fill: "#71717a",
              fontSize: 11,
              formatter: (v: number) => v.toLocaleString(),
            }}
          >
            {cleaned.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.9} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
