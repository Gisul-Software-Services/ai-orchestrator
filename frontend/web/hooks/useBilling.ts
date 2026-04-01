"use client";

import { useQuery } from "@tanstack/react-query";
import type {
  AdminUsageResponse,
  OrgDashboardResponse,
  UsageLogsResponse,
  CurrentUsageResponse,
  UsageByRouteResponse,
  UsageHistoryResponse,
} from "@/types/api";
import { adminFetchJson } from "@/lib/adminApi";

export function useAdminUsageQuery(period: string) {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return useQuery({
    queryKey: ["admin", "billing", "admin-usage", period],
    queryFn: () =>
      adminFetchJson<AdminUsageResponse>(`/api/admin/billing/admin-usage${qs}`),
  });
}

export function useOrgDashboardQuery(orgId: string, period: string) {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return useQuery({
    queryKey: ["admin", "billing", "org-dashboard", orgId, period],
    queryFn: () =>
      adminFetchJson<OrgDashboardResponse>(
        `/api/admin/billing/orgs/${encodeURIComponent(orgId)}/dashboard${qs}`
      ),
    enabled: orgId.trim().length > 0,
  });
}

export function useOrgLogsQuery(
  orgId: string,
  period: string,
  page: number,
  pageSize: number,
  routeFilter: string,
  statusFilter: "all" | "success" | "error"
) {
  const p = new URLSearchParams();
  if (period) p.set("period", period);
  if (page) p.set("page", String(page));
  if (pageSize) p.set("page_size", String(pageSize));
  if (routeFilter) p.set("route", routeFilter);
  if (statusFilter && statusFilter !== "all") p.set("status", statusFilter);
  const qs = p.toString();

  return useQuery({
    queryKey: [
      "admin",
      "billing",
      "org-logs",
      orgId,
      period,
      page,
      pageSize,
      routeFilter,
      statusFilter,
    ],
    queryFn: () =>
      adminFetchJson<UsageLogsResponse>(
        `/api/admin/billing/orgs/${encodeURIComponent(orgId)}/logs${qs ? `?${qs}` : ""}`
      ),
    enabled: orgId.trim().length > 0,
    placeholderData: (prev) => prev,
  });
}

export function useOrgCurrentQuery(orgId: string, period: string) {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return useQuery({
    queryKey: ["admin", "billing", "org-current", orgId, period],
    queryFn: () =>
      adminFetchJson<CurrentUsageResponse>(
        `/api/admin/billing/orgs/${encodeURIComponent(orgId)}/current${qs}`
      ),
    enabled: orgId.trim().length > 0,
  });
}

export function useOrgByRouteQuery(orgId: string, period: string) {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return useQuery({
    queryKey: ["admin", "billing", "org-by-route", orgId, period],
    queryFn: () =>
      adminFetchJson<UsageByRouteResponse>(
        `/api/admin/billing/orgs/${encodeURIComponent(orgId)}/by-route${qs}`
      ),
    enabled: orgId.trim().length > 0,
  });
}

export function useOrgHistoryQuery(orgId: string) {
  return useQuery({
    queryKey: ["admin", "billing", "org-history", orgId],
    queryFn: () =>
      adminFetchJson<UsageHistoryResponse>(
        `/api/admin/billing/orgs/${encodeURIComponent(orgId)}/history`
      ),
    enabled: orgId.trim().length > 0,
  });
}

