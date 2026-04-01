"use client";

import { useMemo } from "react";
import type { FaissStatus } from "@/hooks/useCatalog";

function minutesAgo(iso: string | null) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return null;
  return Math.max(0, Math.round((Date.now() - t) / 60000));
}

export function FaissStatusBadge({
  status,
  stale,
}: {
  status: FaissStatus | null;
  stale: boolean;
}) {
  const mins = useMemo(
    () => minutesAgo(status?.aiml?.last_rebuilt ?? null),
    [status?.aiml?.last_rebuilt]
  );

  const label = stale
    ? "Index may be stale — rebuild recommended"
    : mins == null
      ? "Index status unknown"
      : `Index up to date — last rebuilt: ${mins} min ago`;

  const cls = stale
    ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
    : "border-emerald-500/25 bg-emerald-500/10 text-emerald-200";

  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs ${cls}`}>
      {label}
    </span>
  );
}

