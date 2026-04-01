"use client";

import { Button } from "@/components/ui/button";

export function RevokeKeyDialog({
  open,
  keyHash,
  onCancel,
  onConfirm,
  loading,
}: {
  open: boolean;
  keyHash: string | null;
  onCancel: () => void;
  onConfirm: () => void;
  loading: boolean;
}) {
  if (!open || !keyHash) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 dark:bg-zinc-950/70">
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-5 dark:border-white/10 dark:bg-zinc-950">
        <div className="text-lg font-semibold">Revoke API Key</div>
        <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Are you sure you want to revoke key{" "}
          <span className="font-mono text-zinc-900 dark:text-zinc-200">{keyHash.slice(0, 8)}…</span>?
          This action cannot be undone.
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" className="border-white/10" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading ? "Revoking…" : "Revoke"}
          </Button>
        </div>
      </div>
    </div>
  );
}

