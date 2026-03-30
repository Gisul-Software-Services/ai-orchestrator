/**
 * GET /api/v1/aiml-library/catalog/{catalogId}/preview — OpenML-backed row preview (org-gated in prod).
 */

import { getApiBaseUrl } from "./api";

export type AimlCatalogPreviewResponse = {
  catalog_id: string;
  preview_available: boolean;
  data_preview?: boolean;
  rows: Record<string, unknown>[];
  row_count?: number;
  reason?: string;
};

export async function fetchAimlCatalogPreview(
  catalogId: string,
  opts?: { orgId?: string }
): Promise<AimlCatalogPreviewResponse> {
  const base = getApiBaseUrl().replace(/\/$/, "");
  const headers: Record<string, string> = {};
  const oid = opts?.orgId?.trim();
  if (oid) headers["X-Org-Id"] = oid;
  const url = `${base}/api/v1/aiml-library/catalog/${encodeURIComponent(catalogId)}/preview`;
  const res = await fetch(url, { method: "GET", headers });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`${res.status}: ${t.slice(0, 400)}`);
  }
  return res.json() as Promise<AimlCatalogPreviewResponse>;
}
