"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function EndpointBarChart({
  data,
  height = 260,
}: {
  data: { endpoint: string; value: number }[];
  height?: number;
}) {
  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 16, bottom: 8, left: 120 }}
        >
          <XAxis type="number" tick={{ fill: "#a1a1aa", fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="endpoint"
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            width={120}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(9, 9, 11, 0.95)",
              border: "1px solid rgba(63, 63, 70, 0.6)",
              color: "#fafafa",
              fontSize: 12,
            }}
          />
          <Bar dataKey="value" fill="#22d3ee" radius={[4, 4, 4, 4]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

