"use client";

import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function EndpointFormShell({
  title,
  description,
  submitting,
  error,
  onSubmit,
  onReset,
  children,
}: {
  title: string;
  description: string;
  submitting: boolean;
  error: string | null;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
          <div className="mb-4">
            <div className="text-sm font-semibold text-zinc-50">{title}</div>
            <div className="mt-1 text-xs text-zinc-400">{description}</div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            {children}

            {error ? (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={submitting}>
                {submitting ? "Submitting…" : "Generate"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={submitting}
                onClick={onReset}
              >
                Reset
              </Button>
            </div>
          </form>
        </div>
      </div>

      <div className="lg:col-span-1">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel">
          <div className="mb-2 text-sm font-semibold text-zinc-50">Tips</div>
          <ul className="list-disc space-y-1 pl-4 text-xs text-zinc-400">
            <li>Keep topics specific (e.g. “SQL window functions”).</li>
            <li>Use cache for repeated prompts; disable for fresh samples.</li>
            <li>While polling, you can switch tabs—your session history stays here.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-zinc-300">{label}</div>
      {children}
      {hint ? <div className="text-xs text-zinc-500">{hint}</div> : null}
    </div>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-console-accent focus:ring-1 focus:ring-cyan-400/70"
    />
  );
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className="min-h-[120px] w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-console-accent focus:ring-1 focus:ring-cyan-400/70"
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-console-accent focus:ring-1 focus:ring-cyan-400/70"
    />
  );
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-200">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-zinc-700 bg-zinc-950 text-cyan-400"
      />
      <span>{label}</span>
    </label>
  );
}

