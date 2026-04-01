"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CreateKeyDialog } from "@/components/orgs/CreateKeyDialog";
import { RevokeKeyDialog } from "@/components/orgs/RevokeKeyDialog";
import { useOrgKeysQuery, useRevokeKeyMutation } from "@/hooks/useOrgs";

function fmtDate(v?: string | null) {
  if (!v) return "—";
  return String(v).replace("T", " ").slice(0, 19);
}

export function ApiKeysList({ orgId }: { orgId: string }) {
  const keysQuery = useOrgKeysQuery(orgId);
  const revokeMutation = useRevokeKeyMutation(orgId);
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null);

  const keys = useMemo(() => keysQuery.data?.keys ?? [], [keysQuery.data]);

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
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-medium text-zinc-200">API Keys</div>
        <CreateKeyDialog orgId={orgId} />
      </div>

      {keysQuery.isLoading ? (
        <div className="mt-3 text-sm text-zinc-500">Loading keys…</div>
      ) : keysQuery.isError ? (
        <div className="mt-3 text-sm text-amber-200">
          {keysQuery.error instanceof Error ? keysQuery.error.message : "Failed to load keys"}
        </div>
      ) : keys.length === 0 ? (
        <div className="mt-3 text-sm text-zinc-500">No API keys yet</div>
      ) : (
        <div className="mt-3 overflow-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs text-zinc-500">
              <tr className="border-b border-white/10">
                <th className="py-2 pr-3">Key Hash</th>
                <th className="py-2 pr-3">Label</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Created At</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="text-zinc-200">
              {keys.map((k) => {
                const keyHash = String((k as any).key_hash ?? "");
                const status = String(k.status ?? "unknown").toLowerCase();
                const active = status !== "revoked";
                return (
                  <tr key={`${keyHash}-${k.label}-${k.created_at}-${k.status}`} className="border-b border-white/5">
                    <td className="py-2 pr-3 font-mono text-xs">
                      {keyHash ? `${keyHash.slice(0, 8)}…` : "—"}
                    </td>
                    <td className="py-2 pr-3">{k.label || "default"}</td>
                    <td className="py-2 pr-3">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${
                          active
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                            : "border-red-500/30 bg-red-500/10 text-red-200"
                        }`}
                      >
                        {active ? "active" : "revoked"}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-zinc-400">{fmtDate(k.created_at)}</td>
                    <td className="py-2">
                      {active ? (
                        <Button
                          variant="outline"
                          className="border-white/10"
                          onClick={() => setRevokeTarget(keyHash)}
                          disabled={!keyHash}
                        >
                          Revoke
                        </Button>
                      ) : (
                        <span className="text-zinc-500">—</span>
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

