"use client";

import { format } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type Threshold = {
  value: number;
  color: string;
  label?: string;
};

export type MetricThresholdChartProps<T extends { timestamp: number }> = {
  data: T[];
  dataKey: keyof T;
  height?: number;
  unit?: string;
  yDomain?: [number, number] | ["auto", "auto"] | [number, "auto"] | ["auto", number];
  lineColor?: string;
  thresholds?: Threshold[];
  valueFormatter?: (v: number | null) => string;
};

function defaultValueFormatter(unit?: string) {
  return (v: number | null) => {
    if (v === null || !Number.isFinite(v)) return "—";
    if (!unit) return String(v);
    return `${v}${unit}`;
  };
}

export function MetricThresholdChart<T extends { timestamp: number }>({
  data,
  dataKey,
  height = 200,
  unit,
  yDomain = ["auto", "auto"],
  lineColor = "#22d3ee",
  thresholds,
  valueFormatter,
}: MetricThresholdChartProps<T>) {
  const fmt = valueFormatter ?? defaultValueFormatter(unit);
  const gradientId = `grad-${String(dataKey)}`;

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: 4, right: 10, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.3} />
              <stop offset="60%" stopColor={lineColor} stopOpacity={0.08} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
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
            domain={yDomain as [number, number]}
            tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={32}
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
            formatter={(v) => fmt(typeof v === "number" ? v : null)}
          />
          {thresholds?.map((t, idx) => (
            <ReferenceLine
              key={`${t.value}-${idx}`}
              y={t.value}
              stroke={t.color}
              strokeDasharray="4 4"
              strokeOpacity={0.7}
              ifOverflow="extendDomain"
              label={
                t.label
                  ? {
                      value: t.label,
                      fill: t.color,
                      fontSize: 10,
                      position: "insideTopRight",
                    }
                  : undefined
              }
            />
          ))}
          <Area
            type="monotone"
            dataKey={String(dataKey)}
            dot={false}
            stroke={lineColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
