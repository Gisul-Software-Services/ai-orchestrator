"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";

export type CatalogEntry = {
  id: string;
  name: string;
  source: string;
  category: "tabular" | "nlp" | "cv" | "audio" | "time-series" | "graph";
  pip_install: string;
  import_code: string;
  load_code: string;
  description: string;
  use_case: string;
  features_info: string;
  target: string;
  target_type: string;
  size: string;
  tags: string[];
  domain: string;
  difficulty: Array<"Easy" | "Medium" | "Hard">;
  direct_load: boolean;
};

export type FaissStatus = {
  aiml: { last_rebuilt: string | null; vector_count: number };
  dsa: { last_rebuilt: string | null; vector_count: number };
};

export function useCatalogQuery() {
  return useQuery({
    queryKey: ["admin", "catalog"],
    queryFn: () => adminFetchJson<CatalogEntry[]>("/api/admin/catalog"),
  });
}

export function useCatalogEntryQuery(catalogId: string) {
  return useQuery({
    queryKey: ["admin", "catalog", "entry", catalogId],
    queryFn: () =>
      adminFetchJson<CatalogEntry>(
        `/api/admin/catalog/${encodeURIComponent(catalogId)}`
      ),
    enabled: catalogId.trim().length > 0,
  });
}

export function useFaissStatusQuery() {
  return useQuery({
    queryKey: ["admin", "catalog", "faiss", "status"],
    queryFn: () => adminFetchJson<FaissStatus>("/api/admin/catalog/faiss/status"),
    refetchInterval: 30_000,
  });
}

export function useUpdateEntryMutation(catalogId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entry: CatalogEntry) =>
      adminFetchJson(`/api/admin/catalog/${encodeURIComponent(catalogId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "catalog"] });
      await qc.invalidateQueries({ queryKey: ["admin", "catalog", "entry", catalogId] });
    },
  });
}

export function useCreateEntryMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entry: CatalogEntry) =>
      adminFetchJson(`/api/admin/catalog`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "catalog"] });
    },
  });
}

export function useDeleteEntryMutation(catalogId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      adminFetchJson(`/api/admin/catalog/${encodeURIComponent(catalogId)}`, {
        method: "DELETE",
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "catalog"] });
    },
  });
}

export function useRebuildFaissMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      adminFetchJson<{ ok: boolean; vectors_indexed: number; last_rebuilt: string }>(
        "/api/admin/catalog/faiss/rebuild",
        { method: "POST" }
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "catalog", "faiss", "status"] });
    },
  });
}

