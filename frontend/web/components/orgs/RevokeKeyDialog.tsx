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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-zinc-950 p-5">
        <div className="text-lg font-semibold">Revoke API Key</div>
        <div className="mt-2 text-sm text-zinc-400">
          Are you sure you want to revoke key{" "}
          <span className="font-mono text-zinc-200">{keyHash.slice(0, 8)}…</span>?
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

