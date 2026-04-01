"use client";

import { useMemo } from "react";
import { Button } from "@/components/ui/button";

export type CatalogFilterState = {
  q: string;
  categories: Set<string>;
  domain: string;
  source: string;
  difficulty: Set<string>;
  directLoadMode: "all" | "direct" | "requires";
};

export function CatalogFilters({
  value,
  onChange,
  domains,
  sources,
  onClear,
}: {
  value: CatalogFilterState;
  onChange: (v: CatalogFilterState) => void;
  domains: string[];
  sources: string[];
  onClear: () => void;
}) {
  const categories = ["tabular", "nlp", "cv", "audio", "time-series", "graph"];

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">
        <div className="lg:col-span-2">
          <label className="text-xs text-zinc-500">Search</label>
          <input
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            placeholder="name, id, description…"
            value={value.q}
            onChange={(e) => onChange({ ...value, q: e.target.value })}
          />
        </div>

        <div>
          <label className="text-xs text-zinc-500">Domain</label>
          <select
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.domain}
            onChange={(e) => onChange({ ...value, domain: e.target.value })}
          >
            <option value="">All</option>
            {domains.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-zinc-500">Source</label>
          <select
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.source}
            onChange={(e) => onChange({ ...value, source: e.target.value })}
          >
            <option value="">All</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-zinc-500">Direct load</label>
          <select
            className="mt-1 h-10 w-full rounded-md border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
            value={value.directLoadMode}
            onChange={(e) =>
              onChange({ ...value, directLoadMode: e.target.value as any })
            }
          >
            <option value="all">All</option>
            <option value="direct">Direct load only</option>
            <option value="requires">Requires download</option>
          </select>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-6">
        <div className="lg:col-span-3">
          <div className="text-xs text-zinc-500">Category</div>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-zinc-200">
            {categories.map((c) => (
              <label key={c} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={value.categories.has(c)}
                  onChange={(e) => {
                    const next = new Set(value.categories);
                    if (e.target.checked) next.add(c);
                    else next.delete(c);
                    onChange({ ...value, categories: next });
                  }}
                />
                <span className="font-mono text-xs">{c}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="text-xs text-zinc-500">Difficulty</div>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-zinc-200">
            {["Easy", "Medium", "Hard"].map((d) => (
              <label key={d} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={value.difficulty.has(d)}
                  onChange={(e) => {
                    const next = new Set(value.difficulty);
                    if (e.target.checked) next.add(d);
                    else next.delete(d);
                    onChange({ ...value, difficulty: next });
                  }}
                />
                <span>{d}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-end justify-end">
          <Button variant="outline" className="border-white/10" onClick={onClear}>
            Clear filters
          </Button>
        </div>
      </div>
    </div>
  );
}

