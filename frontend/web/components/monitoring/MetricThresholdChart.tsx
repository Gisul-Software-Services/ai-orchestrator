"use client";

import { format } from "date-fns";
import {
  CartesianGrid,
  Line,
  LineChart,
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
  lineColor = "#22c55e",
  thresholds,
  valueFormatter,
}: MetricThresholdChartProps<T>) {
  const fmt = valueFormatter ?? defaultValueFormatter(unit);

  return (
    <div style={{ height }}>
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
            domain={yDomain as any}
            tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.10)" }}
            tickLine={{ stroke: "rgba(255,255,255,0.10)" }}
            width={36}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(9,9,11,0.92)",
              border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: 10,
              color: "rgba(255,255,255,0.86)",
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
          <Line
            type="monotone"
            dataKey={String(dataKey)}
            dot={false}
            stroke={lineColor}
            strokeWidth={2}
            isAnimationActive={false}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

