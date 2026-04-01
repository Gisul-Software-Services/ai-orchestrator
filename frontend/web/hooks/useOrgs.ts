"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";
import type { ApiKeyRecord, CreateApiKeyResponse } from "@/types/api";

export type OrgsListResponse = {
  period: string;
  orgs: Array<{
    org_id: string;
    total_tokens: number;
    call_count: number;
  }>;
};

export function useOrgsListQuery() {
  return useQuery({
    queryKey: ["admin", "orgs", "list"],
    queryFn: () => adminFetchJson<OrgsListResponse>("/api/admin/orgs"),
  });
}

export function useOrgProfileQuery(orgId: string) {
  return useQuery({
    queryKey: ["admin", "orgs", "profile", orgId],
    queryFn: () =>
      adminFetchJson<Record<string, unknown>>(
        `/api/admin/orgs/${encodeURIComponent(orgId)}/profile`
      ),
    enabled: orgId.trim().length > 0,
  });
}

export function useOrgKeysQuery(orgId: string) {
  return useQuery({
    queryKey: ["admin", "orgs", "keys", orgId],
    queryFn: () =>
      adminFetchJson<{ org_id: string; keys: ApiKeyRecord[] }>(
        `/api/admin/orgs/${encodeURIComponent(orgId)}/keys`
      ),
    enabled: orgId.trim().length > 0,
  });
}

export function useCreateKeyMutation(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { label?: string }) =>
      adminFetchJson<CreateApiKeyResponse>(
        `/api/admin/orgs/${encodeURIComponent(orgId)}/keys`,
        {
          method: "POST",
          body: JSON.stringify({ label: input.label || "default" }),
          headers: { "Content-Type": "application/json" },
        }
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "orgs", "keys", orgId] });
    },
  });
}

export function useRevokeKeyMutation(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyHash: string) =>
      adminFetchJson(
        `/api/admin/orgs/${encodeURIComponent(orgId)}/keys/${encodeURIComponent(
          keyHash
        )}`,
        { method: "DELETE" }
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "orgs", "keys", orgId] });
    },
  });
}

