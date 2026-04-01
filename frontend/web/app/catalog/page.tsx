"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CatalogFilters, type CatalogFilterState } from "@/components/catalog/CatalogFilters";
import { CatalogTable } from "@/components/catalog/CatalogTable";
import { EntrySlideOver } from "@/components/catalog/EntrySlideOver";
import { FaissStatusBadge } from "@/components/catalog/FaissStatusBadge";
import {
  useCatalogQuery,
  useFaissStatusQuery,
  useRebuildFaissMutation,
  type CatalogEntry,
} from "@/hooks/useCatalog";

function uniqSorted(xs: string[]) {
  return Array.from(new Set(xs.filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

export default function CatalogPage() {
  const catalogQuery = useCatalogQuery();
  const faissStatusQuery = useFaissStatusQuery();
  const rebuildMutation = useRebuildFaissMutation();

  const [staleIndex, setStaleIndex] = useState(false);

  const [filters, setFilters] = useState<CatalogFilterState>({
    q: "",
    categories: new Set(),
    domain: "",
    source: "",
    difficulty: new Set(),
    directLoadMode: "all",
  });

  const [slideOpen, setSlideOpen] = useState(false);
  const [slideMode, setSlideMode] = useState<"new" | "edit">("edit");
  const [activeId, setActiveId] = useState<string | null>(null);

  const all = (catalogQuery.data ?? []) as CatalogEntry[];

  const domains = useMemo(() => uniqSorted(all.map((e) => e.domain)), [all]);
  const sources = useMemo(() => uniqSorted(all.map((e) => e.source)), [all]);

  const filtered = useMemo(() => {
    const q = filters.q.toLowerCase().trim();
    return all.filter((e) => {
      if (q) {
        const hay = `${e.name} ${e.id} ${e.description}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (filters.categories.size > 0 && !filters.categories.has(e.category)) return false;
      if (filters.domain && e.domain !== filters.domain) return false;
      if (filters.source && e.source !== filters.source) return false;
      if (filters.difficulty.size > 0) {
        const d = new Set(e.difficulty ?? []);
        const ok = Array.from(filters.difficulty).some((x) => d.has(x as any));
        if (!ok) return false;
      }
      if (filters.directLoadMode === "direct" && !e.direct_load) return false;
      if (filters.directLoadMode === "requires" && e.direct_load) return false;
      return true;
    });
  }, [all, filters]);

  const openNew = () => {
    setSlideMode("new");
    setActiveId(null);
    setSlideOpen(true);
  };

  const openEdit = (id: string) => {
    setSlideMode("edit");
    setActiveId(id);
    setSlideOpen(true);
  };

  const onMutated = () => {
    setStaleIndex(true);
  };

  const deleteById = async (id: string) => {
    const ok = window.confirm("Delete this catalog entry?");
    if (!ok) return;
    try {
      await fetch(`/api/admin/catalog/${encodeURIComponent(id)}`, { method: "DELETE" }).then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
      });
      toast.success("Entry deleted");
      setStaleIndex(true);
      await catalogQuery.refetch();
    } catch {
      toast.error("Delete failed");
    }
  };

  const rebuild = async () => {
    try {
      const res = await rebuildMutation.mutateAsync();
      toast.success(`FAISS index rebuilt — ${res.vectors_indexed} vectors indexed`);
      setStaleIndex(false);
      await faissStatusQuery.refetch();
    } catch {
      toast.error("Rebuild failed");
    }
  };

  const activeEntry = useMemo(() => {
    if (!activeId) return null;
    return all.find((e) => e.id === activeId) ?? null;
  }, [activeId, all]);

  const clearFilters = () =>
    setFilters({
      q: "",
      categories: new Set(),
      domain: "",
      source: "",
      difficulty: new Set(),
      directLoadMode: "all",
    });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-2xl font-semibold">Dataset Catalog</div>
          <div className="mt-1 text-sm text-zinc-400">
            180 datasets across tabular, NLP, CV, audio, time-series, graph
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <FaissStatusBadge status={faissStatusQuery.data ?? null} stale={staleIndex} />
          <Button
            variant="outline"
            className="border-white/10"
            onClick={rebuild}
            disabled={rebuildMutation.isPending}
          >
            {rebuildMutation.isPending ? "Rebuilding…" : "Rebuild FAISS"}
          </Button>
          <Button variant="outline" className="border-white/10" onClick={openNew}>
            Add New Entry
          </Button>
        </div>
      </div>

      <CatalogFilters
        value={filters}
        onChange={setFilters}
        domains={domains}
        sources={sources}
        onClear={clearFilters}
      />

      {catalogQuery.isLoading ? (
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-6 text-sm text-zinc-500">
          Loading catalog…
        </div>
      ) : catalogQuery.isError ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {catalogQuery.error instanceof Error ? catalogQuery.error.message : "Failed to load catalog"}
        </div>
      ) : (
        <CatalogTable
          rows={filtered}
          onEdit={openEdit}
          onRowClick={openEdit}
          onDelete={deleteById}
        />
      )}

      <EntrySlideOver
        open={slideOpen}
        mode={slideMode}
        entryId={activeId}
        initial={slideMode === "edit" ? activeEntry : null}
        onClose={() => setSlideOpen(false)}
        onMutated={() => {
          onMutated();
          catalogQuery.refetch();
        }}
      />
    </div>
  );
}

