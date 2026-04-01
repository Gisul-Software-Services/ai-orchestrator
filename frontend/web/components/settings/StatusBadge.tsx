"use client";

export function StatusBadge({
  ok,
  label,
}: {
  ok: boolean;
  label?: string;
}) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${
        ok
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
          : "border-red-500/30 bg-red-500/10 text-red-200"
      }`}
    >
      {label ?? (ok ? "OK" : "Missing")}
    </span>
  );
}

