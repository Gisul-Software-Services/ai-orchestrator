"use client";

import { useQuery } from "@tanstack/react-query";
import type {
  HealthResponse,
  MetricsOverview,
  StatsResponse,
} from "@/types/api";
import { adminFetchJson } from "@/lib/adminApi";

export function useHealthQuery() {
  return useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => adminFetchJson<HealthResponse>("/api/admin/health"),
    refetchInterval: 10_000,
  });
}

export function useStatsQuery() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: () => adminFetchJson<StatsResponse>("/api/admin/stats"),
    refetchInterval: 30_000,
  });
}

export function useMetricsOverviewQuery() {
  return useQuery({
    queryKey: ["admin", "metrics", "overview"],
    queryFn: () => adminFetchJson<MetricsOverview>("/api/admin/metrics/overview"),
    refetchInterval: 5_000,
  });
}

export function useMetricsGpuQuery() {
  return useQuery({
    queryKey: ["admin", "metrics", "gpu"],
    queryFn: () => adminFetchJson<Record<string, unknown>>("/api/admin/metrics/gpu"),
    refetchInterval: 5_000,
  });
}

export function useMetricsQueuesQuery() {
  return useQuery({
    queryKey: ["admin", "metrics", "queues"],
    queryFn: () =>
      adminFetchJson<Record<string, unknown>>("/api/admin/metrics/queues"),
    refetchInterval: 5_000,
  });
}

export function useMetricsInferenceQuery() {
  return useQuery({
    queryKey: ["admin", "metrics", "inference"],
    queryFn: () =>
      adminFetchJson<Record<string, unknown>>("/api/admin/metrics/inference"),
    refetchInterval: 5_000,
  });
}

