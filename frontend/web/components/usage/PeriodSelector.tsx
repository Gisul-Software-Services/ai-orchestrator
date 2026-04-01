"use client";

import { useMemo } from "react";
import { buildRecentMonths } from "@/components/usage/periodUtils";

export function PeriodSelector({
  value,
  onChange,
  monthsBack = 12,
}: {
  value: string;
  onChange: (v: string) => void;
  monthsBack?: number;
}) {
  const options = useMemo(() => buildRecentMonths(monthsBack), [monthsBack]);

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-zinc-500">Period</label>
      <select
        className="h-9 rounded-md border border-white/10 bg-zinc-950/40 px-3 text-sm text-zinc-200 outline-none focus:border-cyan-500/40"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    </div>
  );
}

