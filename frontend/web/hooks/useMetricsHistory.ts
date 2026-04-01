"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  useMetricsGpuQuery,
  useMetricsInferenceQuery,
  useMetricsQueuesQuery,
} from "@/hooks/useMetrics";

type GpuHistoryPoint = {
  timestamp: number;
  vram_percent: number | null;
  gpu_utilization: number | null;
  temperature_c: number | null;
  power_watts: number | null;
};

type InferenceHistoryPoint = {
  timestamp: number;
  avg_latency_seconds: number | null;
  total_requests: number;
  errors: number;
  cache_hit_rate_percent: number | null;
};

export type QueueHistoryPoint = {
  timestamp: number;
  [queueName: string]: number;
};

function asNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) {
    return Number(v);
  }
  return null;
}

function asInt(v: unknown): number {
  const n = asNumber(v);
  if (n === null) return 0;
  return Math.trunc(n);
}

function clampHistory<T>(arr: T[], max: number) {
  if (arr.length <= max) return;
  arr.splice(0, arr.length - max);
}

/**
 * Maintains rolling 5-minute time series from snapshot metrics.
 * - Pull cadence: every 5 seconds
 * - Window: last 60 points
 * - Storage: refs (avoids re-render per push) + a tick state to trigger chart re-renders
 */
export function useMetricsHistory() {
  const gpuQuery = useMetricsGpuQuery();
  const inferenceQuery = useMetricsInferenceQuery();
  const queuesQuery = useMetricsQueuesQuery();

  const gpuHistoryRef = useRef<GpuHistoryPoint[]>([]);
  const inferenceHistoryRef = useRef<InferenceHistoryPoint[]>([]);
  const queueHistoryRef = useRef<QueueHistoryPoint[]>([]);

  // Latest snapshots stored in refs so interval can read them without needing dependency churn.
  const latestGpuRef = useRef<Record<string, unknown> | null>(null);
  const latestInferenceRef = useRef<Record<string, unknown> | null>(null);
  const latestQueuesRef = useRef<Record<string, unknown> | null>(null);

  const lastInferenceTotalsRef = useRef<{
    totalRequests: number;
    totalGenerationTimeSeconds: number;
    errors: number;
  } | null>(null);

  const [tick, bump] = useState(0);

  useEffect(() => {
    latestGpuRef.current = (gpuQuery.data ?? null) as Record<string, unknown> | null;
  }, [gpuQuery.data]);

  useEffect(() => {
    latestInferenceRef.current = (inferenceQuery.data ?? null) as
      | Record<string, unknown>
      | null;
  }, [inferenceQuery.data]);

  useEffect(() => {
    latestQueuesRef.current = (queuesQuery.data ?? null) as
      | Record<string, unknown>
      | null;
  }, [queuesQuery.data]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const now = Date.now();

      const gpu = latestGpuRef.current ?? {};
      const gpuPoint: GpuHistoryPoint = {
        timestamp: now,
        vram_percent: asNumber(gpu["memory_used_percent"]),
        gpu_utilization: asNumber(gpu["gpu_util_percent"]),
        temperature_c: asNumber(gpu["temperature_c"]),
        power_watts: asNumber(gpu["power_watts"]),
      };
      gpuHistoryRef.current.push(gpuPoint);
      clampHistory(gpuHistoryRef.current, 60);

      const inf = latestInferenceRef.current ?? {};
      const totalRequests = asInt(inf["total_requests"]);
      const errors = asInt(inf["errors"]);
      const totalGenSeconds = asNumber(inf["total_generation_time_seconds"]) ?? 0;
      const cacheHitRate = asNumber(inf["cache_hit_rate_percent"]);

      let avgLatencyWindow: number | null = null;
      const prev = lastInferenceTotalsRef.current;
      if (prev) {
        const dReq = totalRequests - prev.totalRequests;
        const dGen = totalGenSeconds - prev.totalGenerationTimeSeconds;
        if (dReq > 0 && dGen >= 0) {
          avgLatencyWindow = dGen / dReq;
        }
      }
      lastInferenceTotalsRef.current = {
        totalRequests,
        totalGenerationTimeSeconds: totalGenSeconds,
        errors,
      };

      inferenceHistoryRef.current.push({
        timestamp: now,
        avg_latency_seconds: avgLatencyWindow,
        total_requests: totalRequests,
        errors,
        cache_hit_rate_percent: cacheHitRate,
      });
      clampHistory(inferenceHistoryRef.current, 60);

      const q = latestQueuesRef.current ?? {};
      const depths = (q["queue_depths"] ?? {}) as Record<string, unknown>;
      const qp: QueueHistoryPoint = { timestamp: now };
      for (const [k, v] of Object.entries(depths)) {
        qp[k] = asInt(v);
      }
      queueHistoryRef.current.push(qp);
      clampHistory(queueHistoryRef.current, 60);

      bump((x) => x + 1);
    }, 5_000);

    return () => window.clearInterval(id);
  }, []);

  // Memoize array identities so consumers don't accidentally mutate refs.
  const gpuHistory = useMemo(
    () => [...gpuHistoryRef.current],
    [tick]
  );
  const inferenceHistory = useMemo(
    () => [...inferenceHistoryRef.current],
    [tick]
  );
  const queueHistory = useMemo(
    () => [...queueHistoryRef.current],
    [tick]
  );

  return {
    gpuHistory,
    inferenceHistory,
    queueHistory,
    gpuQuery,
    inferenceQuery,
    queuesQuery,
  };
}

