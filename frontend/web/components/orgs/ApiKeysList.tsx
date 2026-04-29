"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CreateKeyDialog } from "@/components/orgs/CreateKeyDialog";
import { RevokeKeyDialog } from "@/components/orgs/RevokeKeyDialog";
import { useOrgKeysQuery, useRevokeKeyMutation } from "@/hooks/useOrgs";
import { cn } from "@/lib/utils";
import { Key, RefreshCw, ShieldOff } from "lucide-react";

function fmtDate(v?: string | null) {
  if (!v) return "—";
  return String(v).replace("T", " ").slice(0, 19);
}

function fmtLastUsed(v?: string | null) {
  if (!v) return "Never";
  return String(v).replace("T", " ").slice(0, 19);
}

export function ApiKeysList({ orgId }: { orgId: string }) {
  const keysQuery = useOrgKeysQuery(orgId);
  const revokeMutation = useRevokeKeyMutation(orgId);
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null);

  const keys = useMemo(() => keysQuery.data?.keys ?? [], [keysQuery.data]);
  const activeKeys = keys.filter((k) => k.status !== "revoked");
  const revokedKeys = keys.filter((k) => k.status === "revoked");

  const revoke = async () => {
    if (!revokeTarget) return;
    try {
      await revokeMutation.mutateAsync(revokeTarget);
      toast.success("API key revoked");
      setRevokeTarget(null);
    } catch {
      toast.error("Failed to revoke API key");
    }
  };

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5 backdrop-blur-sm">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Key className="h-4 w-4 text-console-accent" strokeWidth={1.5} />
          <div className="text-sm font-semibold text-zinc-100">API Keys</div>
          {keys.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                {activeKeys.length} active
              </span>
              {revokedKeys.length > 0 && (
                <span className="rounded-full border border-zinc-700/60 bg-zinc-800/60 px-2 py-0.5 text-[11px] text-zinc-500">
                  {revokedKeys.length} revoked
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="h-8 border-zinc-700/60 px-2.5 text-xs hover:border-zinc-600"
            onClick={() => keysQuery.refetch()}
            disabled={keysQuery.isFetching}
          >
            <RefreshCw className={cn("h-3 w-3", keysQuery.isFetching && "animate-spin")} />
          </Button>
          <CreateKeyDialog orgId={orgId} />
        </div>
      </div>

      {keysQuery.isLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-zinc-800/40" />
          ))}
        </div>
      ) : keysQuery.isError ? (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          {keysQuery.error instanceof Error ? keysQuery.error.message : "Failed to load keys"}
        </div>
      ) : keys.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <Key className="h-8 w-8 text-zinc-700" strokeWidth={1} />
          <div className="text-sm text-zinc-500">No API keys yet</div>
          <div className="text-xs text-zinc-600">Create a key to allow API access for this org</div>
        </div>
      ) : (
        <div className="overflow-auto rounded-lg border border-zinc-800/60">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800/60">
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Label</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Key (prefix)</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Status</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Created</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Last Used</th>
                <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k, idx) => {
                const keyHash = String((k as any).key_hash ?? (k as any).key_prefix ?? "");
                const status = String(k.status ?? "unknown").toLowerCase();
                const active = status !== "revoked";
                return (
                  <tr
                    key={`${keyHash}-${idx}`}
                    className={cn(
                      "border-b border-zinc-800/40 transition-colors",
                      active ? "hover:bg-zinc-800/20" : "opacity-50"
                    )}
                  >
                    <td className="px-4 py-3">
                      <span className="font-medium text-zinc-200">{k.label || "default"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-zinc-400">
                        {keyHash ? `${keyHash.slice(0, 12)}…` : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          active
                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                            : "border-zinc-700/60 bg-zinc-800/60 text-zinc-500"
                        )}
                      >
                        <span className={cn("h-1.5 w-1.5 rounded-full", active ? "bg-emerald-400" : "bg-zinc-600")} />
                        {active ? "Active" : "Revoked"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500">{fmtDate(k.created_at)}</td>
                    <td className="px-4 py-3 text-xs text-zinc-500">{fmtLastUsed(k.last_used_at)}</td>
                    <td className="px-4 py-3">
                      {active ? (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 bg-red-500/5 px-2.5 py-1 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
                          onClick={() => setRevokeTarget(keyHash)}
                          disabled={!keyHash}
                        >
                          <ShieldOff className="h-3 w-3" />
                          Revoke
                        </button>
                      ) : (
                        <span className="text-xs text-zinc-600">
                          {k.revoked_at ? fmtDate(k.revoked_at) : "—"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <RevokeKeyDialog
        open={Boolean(revokeTarget)}
        keyHash={revokeTarget}
        onCancel={() => setRevokeTarget(null)}
        onConfirm={revoke}
        loading={revokeMutation.isPending}
      />
    </div>
  );
}
