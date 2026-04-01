"use client";

import type { CatalogEntry } from "@/hooks/useCatalog";
import { TagInput } from "@/components/catalog/TagInput";
import { Button } from "@/components/ui/button";

type FieldErrors = Record<string, string>;

function fieldError(errors: FieldErrors | null | undefined, name: string) {
  return errors?.[name] ?? null;
}

function Err({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <div className="mt-1 text-xs text-red-300">{msg}</div>;
}

export function EntryForm({
  mode,
  value,
  onChange,
  errors,
  onSave,
  onCancel,
  saving,
  onDelete,
}: {
  mode: "new" | "edit";
  value: CatalogEntry;
  onChange: (v: CatalogEntry) => void;
  errors: FieldErrors | null;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  onDelete?: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3">
        <div>
          <label className="text-xs text-zinc-500">id</label>
          <input
            readOnly={mode === "edit"}
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 font-mono text-sm text-zinc-200 disabled:opacity-60"
            value={value.id}
            onChange={(e) => onChange({ ...value, id: e.target.value })}
          />
          <Err msg={fieldError(errors, "id")} />
        </div>
        <div>
          <label className="text-xs text-zinc-500">name</label>
          <input
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
          />
          <Err msg={fieldError(errors, "name")} />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs text-zinc-500">source</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.source}
              onChange={(e) => onChange({ ...value, source: e.target.value })}
            />
            <Err msg={fieldError(errors, "source")} />
          </div>
          <div>
            <label className="text-xs text-zinc-500">category</label>
            <select
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.category}
              onChange={(e) =>
                onChange({ ...value, category: e.target.value as any })
              }
            >
              {["tabular", "nlp", "cv", "audio", "time-series", "graph"].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <Err msg={fieldError(errors, "category")} />
          </div>
        </div>
        <div>
          <label className="text-xs text-zinc-500">pip_install</label>
          <input
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 font-mono text-sm text-zinc-200"
            value={value.pip_install}
            onChange={(e) => onChange({ ...value, pip_install: e.target.value })}
          />
          <Err msg={fieldError(errors, "pip_install")} />
        </div>
        <div>
          <label className="text-xs text-zinc-500">import_code</label>
          <textarea
            className="mt-1 min-h-[90px] w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 font-mono text-sm text-zinc-200"
            value={value.import_code}
            onChange={(e) => onChange({ ...value, import_code: e.target.value })}
          />
          <Err msg={fieldError(errors, "import_code")} />
        </div>
        <div>
          <label className="text-xs text-zinc-500">load_code</label>
          <textarea
            className="mt-1 min-h-[90px] w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 font-mono text-sm text-zinc-200"
            value={value.load_code}
            onChange={(e) => onChange({ ...value, load_code: e.target.value })}
          />
          <Err msg={fieldError(errors, "load_code")} />
        </div>
        {[
          "description",
          "use_case",
        ].map((k) => (
          <div key={k}>
            <label className="text-xs text-zinc-500">{k}</label>
            <textarea
              className="mt-1 min-h-[90px] w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
              value={(value as any)[k] as string}
              onChange={(e) => onChange({ ...(value as any), [k]: e.target.value })}
            />
            <Err msg={fieldError(errors, k)} />
          </div>
        ))}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs text-zinc-500">features_info</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.features_info}
              onChange={(e) =>
                onChange({ ...value, features_info: e.target.value })
              }
            />
            <Err msg={fieldError(errors, "features_info")} />
          </div>
          <div>
            <label className="text-xs text-zinc-500">domain</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.domain}
              onChange={(e) => onChange({ ...value, domain: e.target.value })}
            />
            <Err msg={fieldError(errors, "domain")} />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="text-xs text-zinc-500">target</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.target}
              onChange={(e) => onChange({ ...value, target: e.target.value })}
            />
            <Err msg={fieldError(errors, "target")} />
          </div>
          <div>
            <label className="text-xs text-zinc-500">target_type</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.target_type}
              onChange={(e) =>
                onChange({ ...value, target_type: e.target.value })
              }
            />
            <Err msg={fieldError(errors, "target_type")} />
          </div>
          <div>
            <label className="text-xs text-zinc-500">size</label>
            <input
              className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={value.size}
              onChange={(e) => onChange({ ...value, size: e.target.value })}
            />
            <Err msg={fieldError(errors, "size")} />
          </div>
        </div>
        <div>
          <label className="text-xs text-zinc-500">tags</label>
          <div className="mt-1">
            <TagInput value={value.tags} onChange={(tags) => onChange({ ...value, tags })} />
          </div>
          <Err msg={fieldError(errors, "tags")} />
        </div>
        <div>
          <label className="text-xs text-zinc-500">difficulty</label>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-zinc-200">
            {(["Easy", "Medium", "Hard"] as const).map((d) => (
              <label key={d} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={value.difficulty.includes(d)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? Array.from(new Set([...value.difficulty, d]))
                      : value.difficulty.filter((x) => x !== d);
                    onChange({ ...value, difficulty: next as any });
                  }}
                />
                <span>{d}</span>
              </label>
            ))}
          </div>
          <Err msg={fieldError(errors, "difficulty")} />
        </div>
        <div className="flex items-center justify-between rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-white/10 dark:bg-white/5">
          <div>
            <div className="text-sm text-zinc-900 dark:text-zinc-200">Direct load</div>
            <div className="text-xs text-zinc-500">
              If enabled, dataset can be loaded without manual download.
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-zinc-900 dark:text-zinc-200">
            <input
              type="checkbox"
              checked={value.direct_load}
              onChange={(e) => onChange({ ...value, direct_load: e.target.checked })}
            />
            <span>{value.direct_load ? "yes" : "no"}</span>
          </label>
          <Err msg={fieldError(errors, "direct_load")} />
        </div>
      </div>

      <div className="flex flex-wrap justify-end gap-2 border-t border-white/10 pt-4">
        {mode === "edit" && onDelete ? (
          <Button variant="outline" className="border-red-500/30 text-red-200 hover:bg-red-500/10" onClick={onDelete}>
            Delete
          </Button>
        ) : null}
        <Button variant="outline" className="border-white/10" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={onSave} disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}

