"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useRagHealthQuery, useRebuildIndexMutation, useIngestMutation } from "@/hooks/useRag";
import { ArrowRight, CheckCircle2, Database, RefreshCw, Upload, XCircle, AlertCircle } from "lucide-react";

const COMPETENCIES = [
  { id: "dsa", label: "DSA", description: "Data Structures & Algorithms problems", available: true },
  { id: "aiml", label: "AIML", description: "AI/ML datasets for question generation", available: true },
  { id: "devops", label: "DevOps", description: "DevOps and infrastructure scenarios", available: true },
  { id: "cloud", label: "Cloud", description: "Cloud architecture and services", available: true },
  { id: "sql", label: "SQL", description: "SQL query problems (RAG + reword)", available: true },
  { id: "data_engineering", label: "Data Engineering", description: "Data pipeline and engineering problems", available: false },
  { id: "design", label: "Design", description: "System design problems", available: false },
  { id: "prompt_engineering", label: "Prompt Engineering", description: "Prompt engineering tasks", available: false },
  { id: "fullstack", label: "Full Stack", description: "Full stack development problems", available: false },
];

function StatusBadge({ loaded }: { loaded: boolean }) {
  if (loaded) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
        <CheckCircle2 className="h-3 w-3" /> Loaded
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
      <XCircle className="h-3 w-3" /> Not loaded
    </span>
  );
}

export default function RagPage() {
  const router = useRouter();
  const healthQuery = useRagHealthQuery();
  const rebuildMutation = useRebuildIndexMutation();
  const ingestMutation = useIngestMutation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const [rebuildingFor, setRebuildingFor] = useState<string | null>(null);

  const indexes = healthQuery.data?.indexes ?? {};
  const ragOnline = healthQuery.data?.status === "ok";

  const handleRebuild = async (competency: string) => {
    const confirmed = window.confirm(
      `Rebuild FAISS index for '${competency}'? This will re-embed all catalog entries and may take 30-60 seconds.`
    );
    if (!confirmed) return;
    setRebuildingFor(competency);
    try {
      const res = await rebuildMutation.mutateAsync(competency);
      toast.success(`Rebuilt '${competency}' — ${res.vectors} vectors in ${res.time_seconds}s`);
    } catch {
      toast.error(`Rebuild failed for '${competency}'`);
    } finally {
      setRebuildingFor(null);
    }
  };

  const handleUpload = (competency: string) => {
    setUploadingFor(competency);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFor) return;
    e.target.value = "";

    try {
      const text = await file.text();
      const entries = JSON.parse(text);
      if (!Array.isArray(entries)) {
        toast.error("JSON must be an array of entries");
        return;
      }
      const res = await ingestMutation.mutateAsync({ competency: uploadingFor, entries });
      toast.success(`Ingested ${res.upserted} entries into '${uploadingFor}' (total: ${res.total_catalog})`);
    } catch (err) {
      toast.error(`Upload failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploadingFor(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-2xl font-semibold">RAG Management</div>
          <div className="mt-1 text-sm text-zinc-400">
            Manage FAISS indexes and dataset catalogs for all competencies
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
            ragOnline
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : healthQuery.isLoading
              ? "border-zinc-700 bg-zinc-800 text-zinc-400"
              : "border-red-500/30 bg-red-500/10 text-red-300"
          }`}>
            <span className={`h-2 w-2 rounded-full ${ragOnline ? "bg-emerald-400" : healthQuery.isLoading ? "bg-zinc-500" : "bg-red-400"}`} />
            {healthQuery.isLoading ? "Connecting…" : ragOnline ? "RAG Service Online" : "RAG Service Offline"}
          </span>
          <Button variant="outline" className="border-white/10" onClick={() => healthQuery.refetch()}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Offline warning */}
      {!healthQuery.isLoading && !ragOnline && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            RAG service is not reachable. Make sure it is running on port 7003 and <code className="rounded bg-amber-500/20 px-1">RAG_SERVICE_URL</code> is set correctly.
          </div>
        </div>
      )}

      {/* Competency cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {COMPETENCIES.map((comp) => {
          const stats = indexes[comp.id];
          const isLoaded = stats?.loaded ?? false;
          const isRebuilding = rebuildingFor === comp.id;
          const isUploading = uploadingFor === comp.id && ingestMutation.isPending;

          return (
            <div key={comp.id} className={`rounded-xl border p-5 space-y-4 ${comp.available ? "border-white/10 bg-zinc-950/40" : "border-white/5 bg-zinc-950/20 opacity-60"}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Database className={`h-4 w-4 ${comp.available ? "text-cyan-400" : "text-zinc-600"}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-zinc-100">{comp.label}</span>
                      {!comp.available && (
                        <span className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">Coming soon</span>
                      )}
                    </div>
                    <div className="text-xs text-zinc-500">{comp.description}</div>
                  </div>
                </div>
                {comp.available && <StatusBadge loaded={isLoaded} />}
              </div>

              {comp.available && (
                <>
                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                      <div className="text-xs text-zinc-500">Vectors</div>
                      <div className="mt-0.5 text-lg font-semibold tabular-nums text-zinc-100">
                        {stats?.vectors?.toLocaleString() ?? "—"}
                      </div>
                    </div>
                    <div className="rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                      <div className="text-xs text-zinc-500">Catalog entries</div>
                      <div className="mt-0.5 text-lg font-semibold tabular-nums text-zinc-100">
                        {stats?.catalog_entries?.toLocaleString() ?? "—"}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 text-xs"
                      onClick={() => router.push(`/rag/${comp.id}`)}
                    >
                      <ArrowRight className="mr-1.5 h-3.5 w-3.5" /> Manage
                    </Button>
                    <Button
                      variant="outline"
                      className="border-white/10 text-xs"
                      onClick={() => handleRebuild(comp.id)}
                      disabled={isRebuilding || !ragOnline}
                    >
                      <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isRebuilding ? "animate-spin" : ""}`} />
                      {isRebuilding ? "Rebuilding…" : "Rebuild"}
                    </Button>
                    <Button
                      variant="outline"
                      className="border-white/10 text-xs"
                      onClick={() => handleUpload(comp.id)}
                      disabled={isUploading || !ragOnline}
                    >
                      <Upload className="mr-1.5 h-3.5 w-3.5" />
                      {isUploading ? "…" : "Upload"}
                    </Button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
