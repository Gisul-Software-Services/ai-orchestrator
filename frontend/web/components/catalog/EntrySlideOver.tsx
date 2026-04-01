"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { EntryForm } from "@/components/catalog/EntryForm";
import type { CatalogEntry } from "@/hooks/useCatalog";
import {
  useCreateEntryMutation,
  useDeleteEntryMutation,
  useUpdateEntryMutation,
} from "@/hooks/useCatalog";

type FieldErrors = Record<string, string>;

const EMPTY_ENTRY: CatalogEntry = {
  id: "",
  name: "",
  source: "",
  category: "tabular",
  pip_install: "",
  import_code: "",
  load_code: "",
  description: "",
  use_case: "",
  features_info: "",
  target: "",
  target_type: "",
  size: "",
  tags: [],
  domain: "",
  difficulty: [],
  direct_load: false,
};

function parseFieldErrors(err: unknown): FieldErrors | null {
  if (!(err instanceof Error)) return null;
  const msg = err.message;
  try {
    const jsonStart = msg.indexOf("{");
    if (jsonStart >= 0) {
      const obj = JSON.parse(msg.slice(jsonStart));
      const fields = obj?.detail?.fields ?? obj?.fields;
      if (fields && typeof fields === "object") return fields as FieldErrors;
    }
  } catch {
    // ignore
  }
  return null;
}

export function EntrySlideOver({
  open,
  mode,
  entryId,
  initial,
  onClose,
  onMutated,
}: {
  open: boolean;
  mode: "new" | "edit";
  entryId: string | null;
  initial?: CatalogEntry | null;
  onClose: () => void;
  onMutated: () => void;
}) {
  const [value, setValue] = useState<CatalogEntry>(EMPTY_ENTRY);
  const [errors, setErrors] = useState<FieldErrors | null>(null);
  const updateMutation = useUpdateEntryMutation(entryId ?? "");
  const createMutation = useCreateEntryMutation();
  const deleteMutation = useDeleteEntryMutation(entryId ?? "");

  useEffect(() => {
    if (!open) return;
    setErrors(null);
    if (mode === "new") setValue(EMPTY_ENTRY);
    else if (initial) setValue(initial);
  }, [open, mode, initial]);

  const title = mode === "new" ? "Add New Entry" : "Edit Entry";

  const saving = updateMutation.isPending || createMutation.isPending;

  const save = async () => {
    setErrors(null);
    try {
      if (mode === "new") {
        await createMutation.mutateAsync(value);
        toast.success("Entry added");
        onMutated();
        onClose();
      } else if (entryId) {
        await updateMutation.mutateAsync(value);
        toast.success("Entry updated");
        onMutated();
        onClose();
      }
    } catch (e) {
      const fe = parseFieldErrors(e);
      if (fe) setErrors(fe);
      else toast.error("Save failed");
    }
  };

  const confirmDelete = async () => {
    if (!entryId) return;
    const ok = window.confirm("Delete this catalog entry?");
    if (!ok) return;
    try {
      await deleteMutation.mutateAsync();
      toast.success("Entry deleted");
      onMutated();
      onClose();
    } catch {
      toast.error("Delete failed");
    }
  };

  const canRender = open;
  if (!canRender) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-[720px] overflow-auto border-l border-white/10 bg-zinc-950 p-5">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-lg font-semibold">{title}</div>
            <div className="mt-1 text-xs text-zinc-500">
              {mode === "new"
                ? "Fill all required fields and save."
                : "Edit fields and save changes."}
            </div>
          </div>
          <Button variant="outline" className="border-white/10" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="mt-5">
          <EntryForm
            mode={mode}
            value={value}
            onChange={setValue}
            errors={errors}
            onSave={save}
            onCancel={onClose}
            saving={saving}
            onDelete={mode === "edit" ? confirmDelete : undefined}
          />
        </div>
      </div>
    </div>
  );
}

