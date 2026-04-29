"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Loader2, RotateCcw, Sparkles } from "lucide-react";

// ── Shell ─────────────────────────────────────────────────────────────────────
export function EndpointFormShell({
  title,
  description,
  submitting,
  error,
  onSubmit,
  onReset,
  children,
  tips,
}: {
  title: string;
  description: string;
  submitting: boolean;
  error: string | null;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  children: ReactNode;
  tips?: string[];
}) {
  const defaultTips = tips ?? [
    'Keep topics specific (e.g. "SQL window functions").',
    "Use cache for repeated prompts; disable for fresh samples.",
    "While polling, you can switch tabs — session history stays here.",
  ];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {/* Form panel */}
      <div className="lg:col-span-2">
        <div className="relative overflow-hidden rounded-2xl border border-zinc-800/60 bg-zinc-900/60 backdrop-blur-sm">
          {/* Top accent */}
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

          {/* Header */}
          <div className="border-b border-zinc-800/60 px-5 py-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-400" strokeWidth={1.75} />
              <div>
                <div className="text-sm font-semibold text-zinc-100">{title}</div>
                <div className="text-xs text-zinc-500">{description}</div>
              </div>
            </div>
          </div>

          {/* Form body */}
          <form onSubmit={onSubmit} className="space-y-5 p-5">
            {children}

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-red-400" />
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={submitting}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
                  submitting
                    ? "cursor-not-allowed bg-zinc-800 text-zinc-500"
                    : "bg-cyan-500 text-zinc-950 hover:bg-cyan-400 active:scale-95"
                )}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" strokeWidth={2} />
                    Generate
                  </>
                )}
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={onReset}
                className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-700/60 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-400 transition-all hover:border-zinc-600 hover:text-zinc-200 disabled:opacity-40"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Tips panel */}
      <div className="lg:col-span-1">
        <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/40 p-5">
          <div className="mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-500">Tips</div>
          <ul className="space-y-2.5">
            {defaultTips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan-500/60" />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Field ─────────────────────────────────────────────────────────────────────
export function Field({
  label,
  children,
  hint,
  required,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1">
        <span className="text-xs font-semibold text-zinc-300">{label}</span>
        {required && <span className="text-[10px] text-red-400">*</span>}
      </div>
      {children}
      {hint && <div className="text-[11px] text-zinc-600">{hint}</div>}
    </div>
  );
}

// ── Input components ──────────────────────────────────────────────────────────
const inputBase =
  "w-full rounded-xl border border-zinc-700/60 bg-zinc-950/60 px-3 py-2.5 text-sm text-zinc-100 outline-none placeholder:text-zinc-600 transition-colors focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/20";

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={inputBase} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(inputBase, "min-h-[120px] resize-y")}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(inputBase, "cursor-pointer")}
    />
  );
}

// ── Toggle ────────────────────────────────────────────────────────────────────
export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      {/* Custom toggle */}
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div className={cn(
          "h-5 w-9 rounded-full transition-colors",
          checked ? "bg-cyan-500" : "bg-zinc-700"
        )}>
          <div className={cn(
            "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-4" : "translate-x-0.5"
          )} />
        </div>
      </div>
      <div>
        <div className="text-sm font-medium text-zinc-200">{label}</div>
        {description && <div className="text-xs text-zinc-500">{description}</div>}
      </div>
    </label>
  );
}

// ── Difficulty selector ───────────────────────────────────────────────────────
export function DifficultySelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const options = [
    { value: "Easy",   color: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400", active: "border-emerald-500 bg-emerald-500/20 text-emerald-300" },
    { value: "Medium", color: "border-amber-500/30 bg-amber-500/10 text-amber-400",       active: "border-amber-500 bg-amber-500/20 text-amber-300" },
    { value: "Hard",   color: "border-red-500/30 bg-red-500/10 text-red-400",             active: "border-red-500 bg-red-500/20 text-red-300" },
  ];
  return (
    <div className="flex gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            "flex-1 rounded-xl border px-3 py-2 text-xs font-semibold transition-all",
            value === o.value ? o.active : o.color
          )}
        >
          {o.value}
        </button>
      ))}
    </div>
  );
}

// ── Language chip selector ────────────────────────────────────────────────────
export function LanguageChips({
  options,
  selected,
  onToggle,
}: {
  options: readonly string[];
  selected: string[];
  onToggle: (lang: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((lang) => {
        const active = selected.includes(lang);
        return (
          <button
            key={lang}
            type="button"
            onClick={() => onToggle(lang)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
              active
                ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-300"
                : "border-zinc-700/60 bg-zinc-900/40 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300"
            )}
          >
            {lang}
          </button>
        );
      })}
    </div>
  );
}
