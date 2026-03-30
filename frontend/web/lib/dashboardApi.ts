import { apiGet } from "./api";

/** Shape returned by GET /api/v1/metrics/overview on the FastAPI server. */
export interface MetricsOverview {
  model_loaded: boolean;
  cuda_memory_gb?: number | null;
  gpu: {
    available: boolean;
    error?: string | null;
    gpu_util_percent?: number;
    memory_used_percent?: number;
    memory_used_mb?: number;
    memory_total_mb?: number;
    temperature_c?: number;
    power_watts?: number | null;
  };
  inference: {
    total_requests: number;
    cache_hit_rate_percent: number;
    requests_by_endpoint: Record<string, number>;
  };
  queues: {
    active_jobs: number;
    jobs_in_store: number;
    queue_depths: Record<string, number>;
  };
}

export async function fetchMetricsOverview(): Promise<MetricsOverview> {
  return apiGet<MetricsOverview>("/api/v1/metrics/overview");
}
