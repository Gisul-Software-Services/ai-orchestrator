"use client";

import { useQuery } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";

export type RequestLogItem = {
  request_id: string;
  timestamp: string;
  method: string;
  path: string;
  org_id: string;
  status_code: number;
  latency_ms: number;
  cache_hit: boolean;
  job_id: string | null;
  [k: string]: unknown;
};

export type RequestLogResponse = {
  total: number;
  page: number;
  page_size: number;
  items: RequestLogItem[];
};

export type RequestLogFilters = {
  endpoint?: string;
  org_id?: string;
  status?: "all" | "success" | "error";
  start_date?: string;
  end_date?: string;
  sort_by?: "timestamp" | "latency_ms";
  sort_order?: "asc" | "desc";
};

export function useRequestLogQuery(
  filters: RequestLogFilters,
  page: number,
  pageSize: number,
  autoRefresh: boolean
) {
  const p = new URLSearchParams();
  p.set("page", String(page));
  p.set("page_size", String(pageSize));
  if (filters.endpoint) p.set("endpoint", filters.endpoint);
  if (filters.org_id) p.set("org_id", filters.org_id);
  if (filters.status && filters.status !== "all") p.set("status", filters.status);
  if (filters.start_date) p.set("start_date", filters.start_date);
  if (filters.end_date) p.set("end_date", filters.end_date);
  if (filters.sort_by) p.set("sort_by", filters.sort_by);
  if (filters.sort_order) p.set("sort_order", filters.sort_order);

  return useQuery({
    queryKey: ["admin", "history", filters, page, pageSize, autoRefresh],
    queryFn: () =>
      adminFetchJson<RequestLogResponse>(`/api/admin/history?${p.toString()}`),
    refetchInterval: autoRefresh ? 15_000 : false,
  });
}

