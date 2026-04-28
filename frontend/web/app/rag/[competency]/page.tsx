"use client";

import { useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  useRagHealthQuery,
  useRebuildIndexMutation,
  useIngestMutation,
  useCatalogListQuery,
  useDeleteEntryMutation,
} from "@/hooks/useRag";
import { ArrowLeft, RefreshCw, Upload, Search, Trash2, Eye } from "lucide-react";

const COMPETENCY_LABELS: Record<string, string> = {
  dsa: "DSA",
  aiml: "AIML",
  sql: "SQL",
  data_engineering: "Data Engineering",
  devops: "DevOps",
  cloud: "Cloud",
  design: "Design",
  prompt_engineering: "Prompt Engineering",
  fullstack: "Full Stack",
};

export default function CompetencyPage() {
  const params = useParams();
  const router = useRouter();
  const competency = params.competency as string;
  const label = COMPETENCY_LABELS[competency] ?? competency;

  const healthQuery = useRagHealthQuery();
  const rebuildMutation = useRebuildIndexMutation();
  const ingestMutation = useIngestMutation();
  const deleteMutation = useDeleteEntryMutation(competency);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [viewEntry, setViewEntry] = useState<Record<string, unknown> | null>(null);

  const stats = healthQuery.data?.indexes?.[competency];
  const ragOnline = healthQuery.data?.status === "ok";
  const catalogQuery = useCatalogListQuery(competency, search);
  const entries = (catalogQuery.data?.entries ?? []) as Record<string, unknown>[];

  const handleRebuild = async () => {
    const confirmed = window.confirm(
      `Rebuild FAISS index for '${label}'? This will re-embed all catalog entries and may take 30-60 seconds.`
    );
    if (!confirmed) return;
    setRebuilding(true);
    try {
      const res = await rebuildMutation.mutateAsync(competency);
      toast.success(`Rebuilt '${label}' — ${res.vectors} vectors in ${res.time_seconds}s`);
      healthQuery.refetch();
    } catch {
      toast.error(`Rebuild failed`);
    } finally {
      setRebuilding(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setUploading(true);
    try {
      const text = await file.text();
      const entries = JSON.parse(text);
      if (!Array.isArray(entries)) {
        toast.error("JSON must be an array of entries");
        return;
      }
      const res = await ingestMutation.mutateAsync({ competency, entries });
      toast.success(`Ingested ${res.upserted} entries (total: ${res.total_catalog})`);
      healthQuery.refetch();
      catalogQuery.refetch();
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (entryId: string, name: string) => {
    if (!window.confirm(`Delete '${name}'? This cannot be undone.`)) return;
    try {
      await deleteMutation.mutateAsync(entryId);
      toast.success(`Deleted '${name}'`);
    } catch {
      toast.error("Delete failed");
    }
  };

  const getEntryId = (e: Record<string, unknown>) =>
    (e.id ?? e.title ?? "") as string;

  const getEntryName = (e: Record<string, unknown>) =>
    (e.name ?? e.title ?? e.concept ?? e.id ?? "—") as string;

  const getEntryDifficulty = (e: Record<string, unknown>) => {
    const d = e.difficulty;
    if (!d) return "—";
    if (Array.isArray(d)) return d.join(", ");
    return String(d);
  };

  const getEntryTags = (e: Record<string, unknown>) => {
    const t = e.tags;
    if (Array.isArray(t)) return t.slice(0, 3).join(", ");
    // Cloud uses service field
    if (e.service) return String(e.service);
    return "—";
  };

  // Fixed 3 columns: title/name, difficulty, tags
  const getEntryTitle = (e: Record<string, unknown>) =>
    String(e.title ?? e.name ?? e.concept ?? e.id ?? "—").slice(0, 80);

  const getEntryDiff = (e: Record<string, unknown>) => {
    const d = e.difficulty;
    if (!d) return "—";
    if (Array.isArray(d)) return (d as string[]).join(", ");
    return String(d);
  };

  const getEntryTagsDisplay = (e: Record<string, unknown>) => {
    const t = e.tags;
    if (Array.isArray(t)) return (t as string[]).slice(0, 3).join(", ") || "—";
    if (e.service) return String(e.service);
    return "—";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-white/10" onClick={() => router.push("/rag")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="text-2xl font-semibold">{label} — RAG Catalog</div>
            <div className="mt-1 text-sm text-zinc-400">
              {catalogQuery.data?.total ?? 0} entries · {stats?.vectors?.toLocaleString() ?? "—"} vectors
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="border-white/10"
            onClick={handleRebuild}
            disabled={rebuilding || !ragOnline}
          >
            <RefreshCw className={`mr-1.5 h-4 w-4 ${rebuilding ? "animate-spin" : ""}`} />
            {rebuilding ? "Rebuilding…" : "Rebuild Index"}
          </Button>
          <Button
            variant="outline"
            className="border-white/10"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || !ragOnline}
          >
            <Upload className="mr-1.5 h-4 w-4" />
            {uploading ? "Uploading…" : "Upload JSON"}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Vectors in index</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{stats?.vectors?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Catalog entries</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{catalogQuery.data?.total?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Index status</div>
          <div className="mt-1">
            {stats?.loaded ? (
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Loaded
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-500">
                <span className="h-2 w-2 rounded-full bg-zinc-600" /> Not loaded
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
        <input
          className="h-10 w-full rounded-lg border border-white/10 bg-zinc-900 pl-9 pr-4 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
          placeholder="Search by name, title, tags..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Catalog table */}
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 overflow-hidden">
        {catalogQuery.isLoading ? (
          <div className="px-4 py-8 text-center text-sm text-zinc-500">Loading catalog…</div>
        ) : entries.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-zinc-500">
            {search ? "No entries match your search." : "No entries in catalog. Upload a JSON file to add data."}
          </div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3">Title / Name</th>
                  <th className="px-4 py-3">Difficulty</th>
                  <th className="px-4 py-3">Tags</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {entries.map((entry, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2 font-medium text-cyan-200">{getEntryTitle(entry)}</td>
                    <td className="px-4 py-2 text-xs text-zinc-400">{getEntryDiff(entry)}</td>
                    <td className="px-4 py-2 text-xs text-zinc-400">{getEntryTagsDisplay(entry)}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          className="border-white/10 text-xs h-7 px-2"
                          onClick={() => setViewEntry(entry)}
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="outline"
                          className="border-red-500/30 text-red-300 hover:bg-red-500/10 text-xs h-7 px-2"
                          onClick={() => handleDelete(getEntryId(entry), getEntryName(entry))}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Entry detail modal */}
      {viewEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setViewEntry(null)}>
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-xl border border-white/10 bg-zinc-900 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <div className="font-semibold text-zinc-100">{getEntryName(viewEntry)}</div>
              <Button variant="outline" className="border-white/10 text-xs" onClick={() => setViewEntry(null)}>Close</Button>
            </div>
            <pre className="overflow-auto rounded-lg bg-zinc-950 p-4 text-xs text-zinc-300">
              {JSON.stringify(viewEntry, null, 2)}
            </pre>
          </div>
        </div>
      )}

      <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleFileChange} />
    </div>
  );
}
