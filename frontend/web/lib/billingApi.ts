/**
 * Billing / org usage API (FastAPI ``/billing/v1``).
 * Data is stored in the billing MongoDB database (e.g. ``aaptor_model``).
 */

import { apiGet } from "./api";

export interface OrgProfile {
  orgId?: string;
  name?: string;
  employeeCounter?: number;
  createdAt?: string;
  updatedAt?: string;
  [key: string]: unknown;
}

export interface UsageCurrent {
  org_id: string;
  org_name?: string;
  billing_period: string;
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  call_count?: number;
  cache_hits?: number;
  errors?: number;
  avg_latency_ms?: number;
}

export interface RouteAgg {
  _id: string;
  total_tokens?: number;
  call_count?: number;
  cache_hits?: number;
  avg_latency_ms?: number;
}

export interface HistoryAgg {
  _id: string;
  total_tokens?: number;
  call_count?: number;
}

export interface OrgDashboard {
  org_id: string;
  period: string;
  profile: OrgProfile;
  current: UsageCurrent;
  by_route: RouteAgg[];
  history: HistoryAgg[];
  errors_this_period: number;
}

export interface UsageLogRow {
  request_id?: string;
  org_id?: string;
  org_name?: string;
  org_verified?: boolean;
  job_id?: string;
  route?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  cache_hit?: boolean;
  latency_ms?: number;
  status?: string;
  billing_period?: string;
  created_at?: string;
  client_ip?: string;
  correlation_id?: string;
  model_name?: string;
  api_version?: string;
  error_detail?: string;
  user_agent?: string;
}

export async function fetchOrgDashboard(
  orgId: string,
  period?: string
): Promise<OrgDashboard> {
  const q = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiGet<OrgDashboard>(
    `/billing/v1/orgs/${encodeURIComponent(orgId)}/dashboard${q}`
  );
}

export async function fetchUsageLogs(
  orgId: string,
  opts?: { period?: string; page?: number; page_size?: number }
): Promise<{
  org_id: string;
  period: string;
  page: number;
  logs: UsageLogRow[];
}> {
  const p = new URLSearchParams();
  if (opts?.period) p.set("period", opts.period);
  if (opts?.page != null) p.set("page", String(opts.page));
  if (opts?.page_size != null) p.set("page_size", String(opts.page_size));
  const qs = p.toString();
  return apiGet(
    `/billing/v1/orgs/${encodeURIComponent(orgId)}/usage/logs${qs ? `?${qs}` : ""}`
  );
}

/** Aggregated usage per org for a billing period (admin overview). */
export interface AdminOrgUsageRow {
  _id: string;
  total_tokens?: number;
  call_count?: number;
}

export async function fetchAdminOrgUsage(period?: string): Promise<{
  period: string;
  orgs: AdminOrgUsageRow[];
}> {
  const q = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiGet(`/billing/v1/admin/usage${q}`);
}
