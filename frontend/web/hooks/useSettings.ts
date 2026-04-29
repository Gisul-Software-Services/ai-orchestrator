"use client";

import {
  useHealthQuery,
  useMetricsInferenceQuery,
  useStatsQuery,
} from "@/hooks/useMetrics";
import type { HealthResponse, InferenceMetrics, StatsResponse } from "@/types/api";

export type SettingsData = {
  health: HealthResponse | null;
  stats: StatsResponse | null;
  inference: InferenceMetrics | null;
};

export type SettingsPayload = {
  source: "derived";
  data: SettingsData;
};

export function useSettingsQuery(): {
  isLoading: boolean;
  isError: boolean;
  data: SettingsPayload;
} {
  const healthQ = useHealthQuery();
  const statsQ = useStatsQuery();
  const inferenceQ = useMetricsInferenceQuery();

  return {
    isLoading: healthQ.isLoading || statsQ.isLoading || inferenceQ.isLoading,
    isError: healthQ.isError && statsQ.isError && inferenceQ.isError,
    data: {
      source: "derived",
      data: {
        health: healthQ.data ?? null,
        stats: statsQ.data ?? null,
        inference: inferenceQ.data ?? null,
      },
    },
  };
}
