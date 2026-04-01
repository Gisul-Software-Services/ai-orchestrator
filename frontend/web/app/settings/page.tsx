"use client";

import { useSettingsQuery } from "@/hooks/useSettings";
import { SettingsSection } from "@/components/settings/SettingsSection";
import { ConfigRow } from "@/components/settings/ConfigRow";
import { StatusBadge } from "@/components/settings/StatusBadge";

function maskMongo(v: string) {
  if (!v) return "—";
  return v.replace(/\/\/.*@/, "//***:***@");
}

export default function SettingsPage() {
  const q = useSettingsQuery();
  const source = q.data?.source ?? "derived";
  const health = q.data?.data?.health ?? {};
  const stats = q.data?.data?.stats ?? {};
  const overview = q.data?.data?.overview ?? {};

  const now = new Date();
  const start = stats?.server_start_time ? new Date(stats.server_start_time as string) : null;
  const uptime = start ? Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000)) : null;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Settings</div>
        <div className="mt-1 text-sm text-zinc-400">
          Configuration is managed via environment variables. Restart the service after changes.
        </div>
      </div>

      {source === "derived" ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          No dedicated backend settings endpoint detected. Display is derived from health and stats.
        </div>
      ) : null}

      <SettingsSection title="Model Configuration">
        <ConfigRow label="Model name" value={String((health as any).model_name ?? "—")} copyable />
        <ConfigRow label="Model loaded" value={String((health as any).model_loaded ?? "—")} />
        <ConfigRow label="Quantization info" value={String((health as any).quantization ?? "—")} />
        <ConfigRow label="CUDA device info" value={String((overview as any)?.gpu?.available ? "available" : "unavailable")} />
        <ConfigRow label="VRAM total" value={String((overview as any)?.gpu?.memory_total_mb ?? "—")} />
      </SettingsSection>

      <SettingsSection title="Server Configuration">
        <ConfigRow label="Batch size max" value={String((health as any).batch_size_max ?? "—")} />
        <ConfigRow label="Batch timeout" value={String((health as any).batch_timeout ?? "—")} />
        <ConfigRow label="Cache TTL" value={String((health as any).cache_ttl ?? "—")} />
        <ConfigRow label="Rate limit per org per minute" value={String((health as any).rate_limit_per_org_per_minute ?? "—")} />
      </SettingsSection>

      <SettingsSection title="Asset Paths">
        {[
          ["AIML catalog path", (health as any).aiml_catalog_path],
          ["AIML FAISS index path", (health as any).aiml_faiss_path],
          ["DSA enriched path", (health as any).dsa_enriched_path],
          ["DSA FAISS path", (health as any).dsa_faiss_path],
        ].map(([label, value]) => (
          <div key={String(label)} className="flex items-center justify-between border-b border-white/5 py-2">
            <div className="text-xs text-zinc-500">{label}</div>
            <div className="flex items-center gap-2">
              <span className="max-w-[560px] break-all text-sm text-zinc-200">{String(value ?? "—")}</span>
              <StatusBadge ok={Boolean(value)} />
            </div>
          </div>
        ))}
      </SettingsSection>

      <SettingsSection title="CORS & Security">
        <ConfigRow label="Allowed origins" value={String((health as any).allowed_origins ?? "—")} />
        <ConfigRow label="API key auth status" value={String((health as any).api_key_auth_enabled ?? "enabled")} />
        <ConfigRow label="Org verification required" value={String((health as any).org_verification_required ?? "—")} />
      </SettingsSection>

      <SettingsSection title="Database">
        <ConfigRow label="MongoDB URI" value={maskMongo(String((health as any).mongodb_uri ?? ""))} />
        <ConfigRow label="Billing DB name" value={String((health as any).billing_db_name ?? "—")} />
        <ConfigRow label="Org DB name" value={String((health as any).organization_db_name ?? "—")} />
        <div className="flex items-center justify-between border-b border-white/5 py-2">
          <div className="text-xs text-zinc-500">Connection status</div>
          <StatusBadge ok={!q.isError} label={!q.isError ? "Connected" : "Unavailable"} />
        </div>
      </SettingsSection>

      <SettingsSection title="Environment">
        <ConfigRow label="Node/Python version info" value={String((health as any).runtime_versions ?? "—")} />
        <ConfigRow label="Docker container info" value={String((health as any).docker_info ?? "—")} />
        <ConfigRow label="Server start time" value={String(stats?.server_start_time ?? "—")} />
        <ConfigRow label="Uptime (seconds)" value={uptime == null ? "—" : String(uptime)} />
        <ConfigRow label="Current server time" value={now.toISOString()} />
      </SettingsSection>
    </div>
  );
}
