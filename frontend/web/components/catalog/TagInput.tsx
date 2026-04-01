"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";

export function TagInput({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  const tags = useMemo(
    () => value.map((t) => t.trim()).filter((t) => t.length > 0),
    [value]
  );

  const addFromDraft = () => {
    const parts = draft
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (parts.length === 0) return;
    const next = Array.from(new Set([...tags, ...parts]));
    onChange(next);
    setDraft("");
  };

  const remove = (t: string) => {
    onChange(tags.filter((x) => x !== t));
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          className="h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
          placeholder="comma,separated,tags"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addFromDraft();
            }
          }}
        />
        <Button variant="outline" className="border-white/10" onClick={addFromDraft}>
          Add
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-200"
          >
            <span className="font-mono">{t}</span>
            <button
              type="button"
              className="text-zinc-400 hover:text-zinc-200"
              onClick={() => remove(t)}
              aria-label={`Remove ${t}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

