"use client";

import type { GenerateMeta } from "@/lib/generation";
import { GeneratedOutput } from "./generated/GeneratedOutput";

export function ResponseView({
  data,
  meta,
  orgIdForApi = "",
}: {
  data: unknown;
  meta?: GenerateMeta | null;
  /** Sent as X-Org-Id on AIML catalog preview refresh (must match org gate when enabled). */
  orgIdForApi?: string;
}) {
  return (
    <GeneratedOutput
      data={data}
      meta={meta ?? undefined}
      orgIdForApi={orgIdForApi}
    />
  );
}
