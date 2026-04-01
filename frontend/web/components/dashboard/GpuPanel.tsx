"use client";

import { differenceInSeconds, formatDistanceStrict } from "date-fns";
import { StatsCard } from "./StatsCard";
import type { HealthResponse, MetricsOverview } from "@/types/api";

function gbFromMb(mb: number | null | undefined) {
  if (typeof mb !== "number") return null;
  return mb / 1024;
}

function pct(n: number | null | undefined) {
  return typeof n === "number" ? n : null;
}

export function GpuPanel({
  health,
  overview,
  loading,
  unreachable,
}: {
  health: HealthResponse | null;
  overview: MetricsOverview | null;
  loading: boolean;
  unreachable: boolean;
}) {
  const modelLoaded = health?.model_loaded ?? overview?.model_loaded ?? false;

  const startIso = (overview as any)?.inference?.server_start_time as
    | string
    | undefined;
  const uptime =
    startIso && !Number.isNaN(Date.parse(startIso))
      ? formatDistanceStrict(new Date(startIso), new Date(), { addSuffix: true })
          .replace("ago", "")
          .trim()
      : null;

  const gpu = overview?.gpu;
  const usedGb = gbFromMb(gpu?.memory_used_mb);
  const totalGb = gbFromMb(gpu?.memory_total_mb);
  const memPct = pct(gpu?.memory_used_percent);
  const utilPct = pct(gpu?.gpu_util_percent);
  const tempC = pct(gpu?.temperature_c);

  const memIndicator =
    memPct === null
      ? "zinc"
      : memPct > 90
        ? "red"
        : memPct > 70
          ? "amber"
          : "emerald";
  const tempIndicator =
    tempC === null
      ? "zinc"
      : tempC > 85
        ? "red"
        : tempC > 70
          ? "amber"
          : "emerald";

  const utilIndicator =
    utilPct === null ? "zinc" : utilPct > 90 ? "amber" : "cyan";

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
      <StatsCard
        title="Model status"
        loading={loading}
        indicatorColor={unreachable ? "zinc" : modelLoaded ? "emerald" : "red"}
        value={
          unreachable ? "Unreachable" : modelLoaded ? "Loaded" : "Not loaded"
        }
        subtitle={uptime ? `Uptime ${uptime}` : undefined}
      />

      <StatsCard
        title="GPU VRAM"
        loading={loading}
        indicatorColor={memIndicator}
        value={
          usedGb !== null && totalGb !== null
            ? `${usedGb.toFixed(2)} / ${totalGb.toFixed(2)} GB`
            : "—"
        }
        subtitle={memPct !== null ? `${memPct.toFixed(2)}% used` : undefined}
      />

      <StatsCard
        title="GPU temperature"
        loading={loading}
        indicatorColor={tempIndicator}
        value={tempC !== null ? `${tempC.toFixed(0)}°C` : "—"}
        subtitle={
          typeof gpu?.power_watts === "number"
            ? `${gpu.power_watts.toFixed(0)} W`
            : undefined
        }
      />

      <StatsCard
        title="GPU utilisation"
        loading={loading}
        indicatorColor={utilIndicator}
        value={utilPct !== null ? `${utilPct.toFixed(0)}%` : "—"}
        subtitle={gpu?.available ? "NVML OK" : gpu?.error ? "NVML error" : ""}
      />
    </div>
  );
}

