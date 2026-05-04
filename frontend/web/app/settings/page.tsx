"use client";

import { useState } from "react";
import { formatDistanceStrict } from "date-fns";
import { useSettingsQuery } from "@/hooks/useSettings";
import { Skeleton, PageLoader } from "@/components/ui/skeleton";
import type { HealthResponse, InferenceMetrics, StatsResponse } from "@/types/api";
import {
  Activity, AlertTriangle, BarChart3, CheckCircle2,
  Clock, Cpu, Database, MemoryStick, RefreshCw,
  Server, Shield, TrendingUp, XCircle, Zap, Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── helpers ───────────────────────────────────────────────────────────────────
function fmt(v: unknown): string {
  if (v === null || v === undefined) return "Not configured";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  const s = String(v).trim();
  return s === "" ? "Not configured" : s;
}

function fmtUptime(startIso: string | null | undefined): string {
  if (!startIso) return "—";
  const parsed = Date.parse(startIso);
  if (Number.isNaN(parsed)) return "—";
  const sec = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  if (sec < 60) return `${sec}s`;
  return formatDistanceStrict(new Date(startIso), new Date(), { addSuffix: false });
}

function fmtNum(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString();
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${n.toFixed(2)}%`;
}

// ── Stat card ─────────────────────────────────────────────────────────────────
type Accent = "cyan" | "violet" | "emerald" | "red" | "amber" | "zinc";

const A: Record<Accent, { border: string; text: string; icon: string; top: string }> = {
  cyan:    { border: "border-cyan-500/20",    text: "text-cyan-400",    icon: "text-cyan-500/70",    top: "#22d3ee" },
  violet:  { border: "border-violet-500/20",  text: "text-violet-400",  icon: "text-violet-500/70",  top: "#a78bfa" },
  emerald: { border: "border-emerald-500/20", text: "text-emerald-400", icon: "text-emerald-500/70", top: "#34d399" },
  red:     { border: "border-red-500/20",     text: "text-red-400",     icon: "text-red-500/70",     top: "#f87171" },
  amber:   { border: "border-amber-500/20",   text: "text-amber-400",   icon: "text-amber-500/70",   top: "#fbbf24" },
  zinc:    { border: "border-zinc-800/60",    text: "text-zinc-300",    icon: "text-zinc-600",       top: "#52525b" },
};

function StatCard({ icon: Icon, label, value, sub, accent = "zinc" }: {
  icon: React.ElementType; label: string; value: string; sub?: string; accent?: Accent;
}) {
  const a = A[accent];
  return (
    <div className={cn("relative overflow-hidden rounded-xl border bg-zinc-900/60 p-4 backdrop-blur-sm", a.border)}>
      <div className="absolute inset-x-0 top-0 h-px opacity-60"
        style={{ background: `linear-gradient(90deg,transparent,${a.top}60,transparent)` }} />
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">{label}</span>
        <Icon className={cn("h-4 w-4", a.icon)} strokeWidth={1.5} />
      </div>
      <div className={cn("text-2xl font-bold tabular-nums", a.text)}>{value}</div>
      {sub && <div className="mt-1 text-xs text-zinc-600">{sub}</div>}
    </div>
  );
}

// ── Section ───────────────────────────────────────────────────────────────────
function Section({ icon: Icon, title, sub, children }: {
  icon: React.ElementType; title: string; sub?: string; children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/50 backdrop-blur-sm">
      <div className="flex items-center gap-3 border-b border-zinc-800/60 px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800/60 bg-zinc-900">
          <Icon className="h-4 w-4 text-cyan-400" strokeWidth={1.75} />
        </div>
        <div>
          <div className="text-sm font-semibold text-zinc-100">{title}</div>
          {sub && <div className="text-xs text-zinc-600">{sub}</div>}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

// ── Row ───────────────────────────────────────────────────────────────────────
function Row({ label, value, mono = false, accent }: {
  label: string; value: string; mono?: boolean; accent?: Accent;
}) {
  const textCls = accent ? A[accent].text : "text-zinc-200";
  return (
    <div className="flex items-center justify-between border-b border-zinc-800/40 py-2.5 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={cn("text-sm font-medium", mono && "font-mono text-xs", textCls)}>
        {value}
      </span>
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────
function Badge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
      ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
         : "border-red-500/30 bg-red-500/10 text-red-300"
    )}>
      <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-emerald-400" : "bg-red-400")} />
      {label ?? (ok ? "OK" : "Error")}
    </span>
  );
}

// ── Queue bar ─────────────────────────────────────────────────────────────────
function QueueBar({ name, depth, max }: { name: string; depth: number; max: number }) {
  const color = depth === 0 ? "bg-zinc-700" : depth <= 5 ? "bg-emerald-400" : depth <= 20 ? "bg-amber-400" : "bg-red-400";
  const text  = depth === 0 ? "text-zinc-600" : depth <= 5 ? "text-emerald-400" : depth <= 20 ? "text-amber-400" : "text-red-400";
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="w-28 shrink-0 font-mono text-xs text-zinc-400">{name}</span>
      <div className="flex-1 h-1.5 rounded-full bg-zinc-800">
        <div className={cn("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${Math.max(depth > 0 ? 4 : 0, (depth / max) * 100)}%` }} />
      </div>
      <span className={cn("w-6 text-right text-xs font-bold tabular-nums", text)}>{depth}</span>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const q = useSettingsQuery();
  const health: HealthResponse | null    = q.data.data.health;
  const stats: StatsResponse | null      = q.data.data.stats;
  const inference: InferenceMetrics | null = q.data.data.inference;

  const [clearing, setClearing] = useState(false);
  const [clearResult, setClearResult] = useState<"idle" | "ok" | "error">("idle");

  async function handleClearCache() {
    setClearing(true);
    setClearResult("idle");
    try {
      const res = await fetch("/api/admin/cache/clear", { method: "POST" });
      setClearResult(res.ok ? "ok" : "error");
    } catch {
      setClearResult("error");
    } finally {
      setClearing(false);
      setTimeout(() => setClearResult("idle"), 4000);
    }
  }

  if (q.isLoading) {
    return <PageLoader label="Loading system configuration…" />;
  }

  const modelLoaded = health?.model_loaded ?? false;
  const uptime = fmtUptime(inference?.server_start_time);
  const errorRate = stats?.total_requests && stats.total_requests > 0 && stats.errors != null
    ? (100 * stats.errors) / stats.total_requests : null;

  const queueEntries = Object.entries(health?.queue_sizes ?? {}).sort((a, b) => b[1] - a[1]);
  const maxDepth = Math.max(1, ...queueEntries.map(([, v]) => v));

  return (
    <div className="animate-fade-in space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-3xl font-bold tracking-tight text-zinc-50">Settings</div>
          <div className="mt-1 text-sm text-zinc-500">
            System configuration derived from live endpoints
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-zinc-800/60 bg-zinc-900/60 px-3 py-1.5 text-xs text-zinc-500">
          <RefreshCw className="h-3 w-3" />
          Live data
        </div>
      </div>

      {/* Error banner */}
      {q.isError && (
        <div className="flex items-center gap-3 rounded-2xl border border-amber-500/20 bg-amber-500/5 px-5 py-3 text-sm text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          All backend endpoints are unreachable. Showing last known data.
        </div>
      )}

      {/* Info banner */}
      <div className="flex items-center gap-3 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 px-5 py-3 text-sm text-cyan-300/80">
        <Shield className="h-4 w-4 shrink-0 text-cyan-400" />
        Configuration is derived from health, stats, and inference endpoints. No dedicated settings endpoint is available.
      </div>

      {/* ── System status hero ─────────────────────────────────────────────── */}
      <div className={cn(
        "relative overflow-hidden rounded-2xl border p-6",
        modelLoaded ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"
      )}>
        <div className="absolute inset-x-0 top-0 h-px"
          style={{ background: modelLoaded ? "linear-gradient(90deg,transparent,#34d399,transparent)" : "linear-gradient(90deg,transparent,#f87171,transparent)" }} />
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl opacity-10"
          style={{ background: modelLoaded ? "#34d399" : "#f87171" }} />

        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className={cn(
              "flex h-14 w-14 items-center justify-center rounded-2xl border",
              modelLoaded ? "border-emerald-500/30 bg-emerald-500/10" : "border-red-500/30 bg-red-500/10"
            )}>
              {modelLoaded
                ? <CheckCircle2 className="h-7 w-7 text-emerald-400" strokeWidth={1.5} />
                : <XCircle className="h-7 w-7 text-red-400" strokeWidth={1.5} />}
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Model Status</div>
              <div className={cn("text-3xl font-bold", modelLoaded ? "text-emerald-400" : "text-red-400")}>
                {modelLoaded ? "LOADED" : "NOT LOADED"}
              </div>
              <div className="mt-0.5 text-xs text-zinc-500">
                {health?.status ?? "Unknown"} · {uptime !== "—" ? `Up ${uptime}` : "Uptime unknown"}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">Memory</div>
              <div className="mt-0.5 text-xl font-bold text-zinc-100">
                {health?.memory_gb != null ? `${health.memory_gb.toFixed(1)} GB` : "—"}
              </div>
            </div>
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">Active jobs</div>
              <div className="mt-0.5 text-xl font-bold text-cyan-400">{health?.active_jobs ?? 0}</div>
            </div>
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">In store</div>
              <div className="mt-0.5 text-xl font-bold text-zinc-300">{health?.total_jobs_in_store ?? 0}</div>
            </div>
            <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/60 px-4 py-2.5 text-center">
              <div className="text-[10px] uppercase tracking-widest text-zinc-600">Connection</div>
              <div className="mt-1">
                <Badge ok={!q.isError} label={!q.isError ? "Connected" : "Offline"} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Performance metrics ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={Activity}   label="Total requests"  value={fmtNum(stats?.total_requests)}          sub="All-time"          accent="cyan" />
        <StatCard icon={TrendingUp} label="Cache hit rate"  value={fmtPct(stats?.cache_hit_rate_percent)}  sub="From stats"        accent={stats?.cache_hit_rate_percent != null && stats.cache_hit_rate_percent > 60 ? "emerald" : "amber"} />
        <StatCard icon={BarChart3}  label="Error rate"      value={errorRate != null ? fmtPct(errorRate) : "—"} sub={fmtNum(stats?.errors) + " errors"} accent={errorRate != null && errorRate > 5 ? "red" : "emerald"} />
        <StatCard icon={Zap}        label="Avg batch size"  value={fmtNum(stats?.avg_batch_size)}          sub={fmtNum(stats?.batches_processed) + " batches"} accent="violet" />
      </div>

      {/* ── Inference engine ───────────────────────────────────────────────── */}
      <Section icon={Cpu} title="Inference Engine" sub="Live data from inference endpoint">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-0">
            <Row label="Server start time"         value={fmt(inference?.server_start_time)} mono />
            <Row label="Uptime"                    value={uptime} accent="emerald" />
            <Row label="Total requests"            value={fmtNum(inference?.total_requests)} accent="cyan" />
            <Row label="Total generation time"     value={inference?.total_generation_time_seconds != null ? `${inference.total_generation_time_seconds.toFixed(1)}s` : "—"} />
          </div>
          <div className="space-y-0">
            <Row label="Cache hits"                value={fmtNum(inference?.cache_hits)} accent="emerald" />
            <Row label="Cache misses"              value={fmtNum(inference?.cache_misses)} accent="red" />
            <Row label="Cache hit rate"            value={fmtPct(inference?.cache_hit_rate_percent)} accent="emerald" />
            <Row label="Errors"                    value={fmtNum(inference?.errors)} accent={inference?.errors ? "red" : "zinc"} />
          </div>
        </div>
      </Section>

      {/* ── Runtime stats ──────────────────────────────────────────────────── */}
      <Section icon={BarChart3} title="Runtime Stats" sub="Aggregated from /stats endpoint">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-0">
            <Row label="Total requests"            value={fmtNum(stats?.total_requests)} accent="cyan" />
            <Row label="Batches processed"         value={fmtNum(stats?.batches_processed)} />
            <Row label="Avg batch size"            value={fmtNum(stats?.avg_batch_size)} accent="violet" />
          </div>
          <div className="space-y-0">
            <Row label="Cache hit rate"            value={fmtPct(stats?.cache_hit_rate_percent)} accent="emerald" />
            <Row label="Errors"                    value={fmtNum(stats?.errors)} accent={stats?.errors ? "red" : "zinc"} />
            <Row label="Error rate"                value={errorRate != null ? fmtPct(errorRate) : "—"} accent={errorRate != null && errorRate > 5 ? "red" : "emerald"} />
          </div>
        </div>
      </Section>

      {/* ── Queue snapshot ─────────────────────────────────────────────────── */}
      <Section icon={Database} title="Queue Snapshot" sub="Current queue depths from health endpoint">
        {queueEntries.length === 0 ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-sm text-emerald-400">All queues empty</span>
          </div>
        ) : (
          <div className="space-y-1">
            {queueEntries.map(([name, depth]) => (
              <QueueBar key={name} name={name} depth={depth} max={maxDepth} />
            ))}
          </div>
        )}
      </Section>

      {/* ── Server info ────────────────────────────────────────────────────── */}
      <Section icon={Server} title="Server Info" sub="Runtime environment details">
        <div className="space-y-0">
          <Row label="Service status"              value={fmt(health?.status)} accent={health?.status === "ok" ? "emerald" : "amber"} />
          <Row label="System memory"               value={health?.memory_gb != null ? `${health.memory_gb.toFixed(2)} GB` : "—"} />
          <Row label="Active jobs"                 value={fmtNum(health?.active_jobs)} accent="cyan" />
          <Row label="Total jobs in store"         value={fmtNum(health?.total_jobs_in_store)} />
          <Row label="Server start time"           value={fmt(inference?.server_start_time)} mono />
          <Row label="Uptime"                      value={uptime} accent="emerald" />
          <Row label="Current time (client)"       value={new Date().toISOString()} mono />
          <div className="flex items-center justify-between border-b border-zinc-800/40 py-2.5 last:border-0">
            <span className="text-xs text-zinc-500">Backend connection</span>
            <Badge ok={!q.isError} label={!q.isError ? "Connected" : "Unavailable"} />
          </div>
          <div className="flex items-center justify-between border-b border-zinc-800/40 py-2.5 last:border-0">
            <span className="text-xs text-zinc-500">Model loaded</span>
            <Badge ok={modelLoaded} label={modelLoaded ? "Loaded" : "Not loaded"} />
          </div>
        </div>
      </Section>

      {/* ── Cache management ───────────────────────────────────────────────── */}
      <Section icon={Trash2} title="Cache Management" sub="Clear the inference response cache">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="text-sm text-zinc-200">Clear inference cache</div>
            <div className="text-xs text-zinc-500">
              Removes all cached responses. New requests will be re-generated by the model.
              Current hit rate:{" "}
              <span className="font-medium text-emerald-400">
                {fmtPct(stats?.cache_hit_rate_percent)}
              </span>
            </div>
          </div>
          <button
            onClick={handleClearCache}
            disabled={clearing}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all",
              clearing
                ? "cursor-not-allowed border-zinc-700 bg-zinc-800/60 text-zinc-500"
                : "border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:border-red-500/50"
            )}
          >
            <Trash2 className="h-4 w-4" strokeWidth={1.75} />
            {clearing ? "Clearing…" : "Clear Cache"}
          </button>
        </div>
        {clearResult === "ok" && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5 text-sm text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Cache cleared successfully.
          </div>
        )}
        {clearResult === "error" && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-2.5 text-sm text-red-400">
            <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
            Failed to clear cache. Check backend connection.
          </div>
        )}
      </Section>

    </div>
  );
}
