"use client";

import { formatDistanceStrict } from "date-fns";
import { StatsCard } from "./StatsCard";
import type { HealthResponse, MetricsOverview } from "@/types/api";
import { Cpu, Thermometer, Zap, MemoryStick } from "lucide-react";

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

  const startIso = (overview as { inference?: { server_start_time?: string } } | null)
    ?.inference?.server_start_time;
  const uptime =
    startIso && !Number.isNaN(Date.parse(startIso))
      ? formatDistanceStrict(new Date(startIso), new Date(), { addSuffix: false })
      : null;

  const gpu = overview?.gpu;
  const gpuUnavailable = gpu?.available === false;
  const gpuErrorMsg = gpu?.error ?? "NVML not available";

  const usedGb = gbFromMb(gpu?.memory_used_mb);
  const totalGb = gbFromMb(gpu?.memory_total_mb);
  const memPct = pct(gpu?.memory_used_percent);
  const utilPct = pct(gpu?.gpu_util_percent);
  const tempC = pct(gpu?.temperature_c);

  const memColor =
    gpuUnavailable ? "zinc"
    : memPct === null ? "zinc"
    : memPct > 90 ? "red"
    : memPct > 70 ? "amber"
    : "emerald";

  const tempColor =
    gpuUnavailable ? "zinc"
    : tempC === null ? "zinc"
    : tempC > 85 ? "red"
    : tempC > 70 ? "amber"
    : "emerald";

  const utilColor =
    gpuUnavailable ? "zinc"
    : utilPct === null ? "zinc"
    : utilPct > 90 ? "amber"
    : "cyan";

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatsCard
        title="Model status"
        loading={loading}
        indicatorColor={unreachable ? "zinc" : modelLoaded ? "emerald" : "red"}
        value={unreachable ? "Unreachable" : modelLoaded ? "Loaded" : "Not loaded"}
        subtitle={uptime ? `Up ${uptime}` : health?.memory_gb ? `${health.memory_gb.toFixed(1)} GB RAM` : undefined}
        icon={<Cpu className="h-3.5 w-3.5 text-zinc-600" strokeWidth={1.5} />}
      />

      <StatsCard
        title="GPU VRAM"
        loading={loading}
        indicatorColor={memColor}
        value={
          gpuUnavailable
            ? "Unavailable"
            : usedGb !== null && totalGb !== null
              ? `${usedGb.toFixed(1)} / ${totalGb.toFixed(1)} GB`
              : "—"
        }
        subtitle={
          gpuUnavailable
            ? gpuErrorMsg
            : memPct !== null
              ? `${memPct.toFixed(1)}% used`
              : undefined
        }
        icon={<MemoryStick className="h-3.5 w-3.5 text-zinc-600" strokeWidth={1.5} />}
      />

      <StatsCard
        title="GPU temperature"
        loading={loading}
        indicatorColor={tempColor}
        value={gpuUnavailable ? "Unavailable" : tempC !== null ? `${tempC.toFixed(0)}°C` : "—"}
        subtitle={
          gpuUnavailable
            ? gpuErrorMsg
            : typeof gpu?.power_watts === "number"
              ? `${gpu.power_watts.toFixed(0)} W draw`
              : undefined
        }
        icon={<Thermometer className="h-3.5 w-3.5 text-zinc-600" strokeWidth={1.5} />}
      />

      <StatsCard
        title="GPU utilisation"
        loading={loading}
        indicatorColor={utilColor}
        value={gpuUnavailable ? "Unavailable" : utilPct !== null ? `${utilPct.toFixed(0)}%` : "—"}
        subtitle={
          gpuUnavailable
            ? gpuErrorMsg
            : gpu?.available
              ? "NVML OK"
              : gpu?.error
                ? "NVML error"
                : ""
        }
        icon={<Zap className="h-3.5 w-3.5 text-zinc-600" strokeWidth={1.5} />}
      />
    </div>
  );
}
