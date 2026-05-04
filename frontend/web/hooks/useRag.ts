"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";

export type RagIndexStats = {
  vectors: number;
  catalog_entries: number;
  loaded: boolean;
};

export type RagHealthResponse = {
  status: string;
  loaded_competencies: string[];
  indexes: Record<string, RagIndexStats>;
};

export type RetrieveRequest = {
  competency: string;
  topic: string;
  difficulty: string;
  concepts: string[];
  top_k?: number;
};

export type RetrieveResponse = {
  matched: Record<string, unknown>;
  score: number;
  method: string;
  competency: string;
};

export function useRagHealthQuery() {
  return useQuery({
    queryKey: ["rag", "health"],
    queryFn: () => adminFetchJson<RagHealthResponse>("/api/admin/rag/health"),
    refetchInterval: 30_000,
  });
}

export function useRebuildIndexMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (competency: string) =>
      adminFetchJson<{ competency: string; vectors: number; time_seconds: number }>(
        `/api/admin/rag/rebuild/${competency}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ use_gpu_model: false }) }
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["rag", "health"] });
    },
  });
}

export function useIngestMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ competency, entries }: { competency: string; entries: unknown[] }) =>
      adminFetchJson<{ competency: string; upserted: number; total_catalog: number }>(
        `/api/admin/rag/ingest/${competency}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ entries }),
        }
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["rag", "health"] });
      await qc.invalidateQueries({ queryKey: ["rag", "catalog"] });
    },
  });
}

export function useCatalogListQuery(competency: string, search: string = "") {
  return useQuery({
    queryKey: ["rag", "catalog", competency, search],
    queryFn: () =>
      adminFetchJson<{ competency: string; total: number; entries: unknown[] }>(
        `/api/admin/rag/catalog/${competency}?search=${encodeURIComponent(search)}&limit=500`
      ),
    enabled: competency.length > 0,
  });
}

export function useDeleteEntryMutation(competency: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      adminFetchJson(`/api/admin/rag/catalog/${competency}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entryId }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["rag", "catalog", competency] });
      await qc.invalidateQueries({ queryKey: ["rag", "health"] });
    },
  });
}
