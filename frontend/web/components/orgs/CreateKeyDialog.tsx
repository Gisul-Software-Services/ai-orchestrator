"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useCreateKeyMutation } from "@/hooks/useOrgs";

export function CreateKeyDialog({ orgId }: { orgId: string }) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("default");
  const [rawKey, setRawKey] = useState<string | null>(null);
  const [ack, setAck] = useState(false);
  const mutation = useCreateKeyMutation(orgId);

  const canClose = rawKey === null || ack;

  const closeAll = () => {
    if (!canClose) return;
    setOpen(false);
    setLabel("default");
    setRawKey(null);
    setAck(false);
  };

  const createKey = async () => {
    try {
      const res = await mutation.mutateAsync({ label: label.trim() || "default" });
      setRawKey(res.api_key || "");
      setAck(false);
      toast.success("API key created successfully");
    } catch {
      toast.error("Failed to create API key");
    }
  };

  return (
    <>
      <Button variant="outline" className="border-white/10" onClick={() => setOpen(true)}>
        Create New Key
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/40 p-4 dark:bg-zinc-950/70">
          <div className="w-full max-w-lg rounded-xl border border-zinc-200 bg-white p-5 dark:border-white/10 dark:bg-zinc-950">
            <div className="text-lg font-semibold">Create API Key</div>
            {rawKey ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                  This key will only be shown once. Copy it now.
                </div>
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={rawKey}
                    className="h-10 w-full rounded-md border border-zinc-200 bg-zinc-50 px-3 font-mono text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-200"
                  />
                  <Button
                    variant="outline"
                    className="border-white/10"
                    onClick={() => navigator.clipboard.writeText(rawKey)}
                  >
                    Copy
                  </Button>
                </div>
                <label className="flex items-start gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                  <input
                    type="checkbox"
                    checked={ack}
                    onChange={(e) => setAck(e.target.checked)}
                    className="mt-0.5"
                  />
                  <span>I have copied this key</span>
                </label>
                <div className="flex justify-end">
                  <Button onClick={closeAll} disabled={!canClose}>
                    Close
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Label</label>
                  <input
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    className="h-10 w-full rounded-md border border-zinc-200 bg-zinc-50 px-3 text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-200"
                    placeholder="default"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    className="border-white/10"
                    onClick={closeAll}
                  >
                    Cancel
                  </Button>
                  <Button onClick={createKey} disabled={mutation.isPending}>
                    {mutation.isPending ? "Creating…" : "Create Key"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}

