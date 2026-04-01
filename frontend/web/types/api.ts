// Core system & metrics types

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  memory_gb: number;
  queue_sizes: Record<string, number>;
  active_jobs: number;
  total_jobs_in_store: number;
}

export interface StatsResponse {
  total_requests: number;
  cache_hit_rate_percent: number;
  requests_by_endpoint: Record<string, number>;
  batches_processed: number;
  avg_batch_size: number;
  errors: number;
}

export interface JobRecord {
  status: "pending" | "processing" | "complete" | "failed";
  result?: unknown;
  error?: string | null;
}

// Dashboard metrics

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

// Billing / usage

export interface OrgProfileResponse {
  org: Record<string, unknown>;
}

export interface CurrentUsageResponse {
  org_id: string;
  org_name: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  call_count: number;
  cache_hits: number;
  errors: number;
  avg_latency_ms: number;
  billing_period: string;
}

export interface UsageByRouteRow {
  _id: string;
  total_tokens: number;
  call_count: number;
  cache_hits: number;
  avg_latency_ms: number;
}

export interface UsageByRouteResponse {
  period: string;
  org_id: string;
  routes: UsageByRouteRow[];
}

export interface UsageHistoryRow {
  _id: string;
  total_tokens: number;
  call_count: number;
}

export interface UsageHistoryResponse {
  org_id: string;
  history: UsageHistoryRow[];
}

export interface UsageLogsResponse {
  org_id: string;
  period: string;
  page: number;
  logs: Record<string, unknown>[];
}

export interface OrgDashboardResponse {
  org_id: string;
  period: string;
  profile: Record<string, unknown>;
  current: CurrentUsageResponse;
  by_route: UsageByRouteRow[];
  history: UsageHistoryRow[];
  errors_this_period: number;
}

export interface AdminUsageRow {
  _id: string;
  total_tokens: number;
  call_count: number;
}

export interface AdminUsageResponse {
  period: string;
  orgs: AdminUsageRow[];
}

export interface ApiKeyRecord {
  org_id: string;
  label: string;
  status: string;
  created_at?: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
}

export interface CreateApiKeyResponse {
  org_id: string;
  api_key: string;
  label: string;
  note: string;
}

export interface ListApiKeysResponse {
  org_id: string;
  keys: ApiKeyRecord[];
}

// Existing console/playground registry types (kept for compatibility)

export type ApiEndpointSection = "generation" | "dsa" | "future";

export interface ApiEndpointMeta {
  id: string;
  path: string;
  method: string;
  label: string;
  description: string;
  implemented: boolean;
  section: ApiEndpointSection;
}

