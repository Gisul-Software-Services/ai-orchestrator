/**
 * POST generation + optional job polling (same contract as the REST API).
 */

import { apiGet, apiPost, getApiBaseUrl } from "./api";

export interface JobRecord {
  status: string;
  result?: unknown;
  error?: string | null;
}

export interface GenerateMeta {
  durationMs: number;
  postUrl: string;
  jobId?: string;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

const POLL_MS = 2000;
const MAX_WAIT_MS = 15 * 60 * 1000;

export interface PostGenerateOptions {
  /** Correlation headers (e.g. X-Request-Id, X-Org-Id) — sent on POST and poll GETs */
  headers?: Record<string, string>;
  onProgress?: (
    message: string,
    detail?: { jobId: string; elapsedMs: number; polls: number }
  ) => void;
}

export async function postGenerateOrJob(
  pathSuffix: string,
  body: Record<string, unknown>,
  options?: PostGenerateOptions
): Promise<{ result: unknown; meta: GenerateMeta }> {
  const base = getApiBaseUrl().replace(/\/$/, "");
  const postUrl = `${base}/api/v1/${pathSuffix}`;
  const headerInit = options?.headers as HeadersInit | undefined;

  const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
  options?.onProgress?.("Sending request…");

  const data = await apiPost<Record<string, unknown>>(`/api/v1/${pathSuffix}`, body, {
    headers: headerInit,
  });

  const jobId = data.job_id;
  if (typeof jobId !== "string") {
    const durationMs =
      (typeof performance !== "undefined" ? performance.now() : Date.now()) - t0;
    return {
      result: data,
      meta: { durationMs, postUrl },
    };
  }

  const deadline = Date.now() + MAX_WAIT_MS;
  let polls = 0;
  const pollT0 = Date.now();
  while (Date.now() < deadline) {
    polls += 1;
    const elapsedMs = Date.now() - pollT0;
    options?.onProgress?.(
      `Job running… ${Math.floor(elapsedMs / 1000)}s elapsed (poll ${polls})`,
      { jobId, elapsedMs, polls }
    );
    const job = await apiGet<JobRecord>(`/api/v1/job/${jobId}`, {
      headers: headerInit,
    });
    const st = job.status;
    if (st === "complete") {
      const durationMs =
        (typeof performance !== "undefined" ? performance.now() : Date.now()) - t0;
      if ("result" in job && job.result !== undefined && job.result !== null) {
        return {
          result: job.result,
          meta: { durationMs, postUrl, jobId },
        };
      }
      return { result: job, meta: { durationMs, postUrl, jobId } };
    }
    if (st === "failed" || st === "error") {
      throw new Error(
        typeof job.error === "string" ? job.error : "Generation failed"
      );
    }
    await sleep(POLL_MS);
  }

  throw new Error("Timed out waiting for job to complete");
}

export function getHealthUrl(): string {
  const base = getApiBaseUrl().replace(/\/$/, "");
  return `${base}/health`;
}

export function getStatsUrl(): string {
  const base = getApiBaseUrl().replace(/\/$/, "");
  return `${base}/stats`;
}

export async function postClearCache(): Promise<unknown> {
  return apiPost<unknown>("/api/v1/clear-cache", {});
}
