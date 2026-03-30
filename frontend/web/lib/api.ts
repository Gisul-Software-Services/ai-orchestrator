/**
 * HTTP client for the FastAPI backend.
 */

const DEFAULT_BASE = "http://127.0.0.1:9000";

function normalizeApiBase(raw: string | undefined): string {
  const s = (raw ?? "").trim();
  if (!s || !/^https?:\/\//i.test(s)) {
    return DEFAULT_BASE;
  }
  return s.replace(/\/$/, "");
}

/**
 * Backend origin only (no `/api/v1` suffix). In production, set `NEXT_PUBLIC_API_BASE`
 * to the URL users use to reach the API (scheme + host + port), e.g. `https://api.example.com`.
 */
export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return normalizeApiBase(process.env.NEXT_PUBLIC_API_BASE);
  }
  return normalizeApiBase(
    process.env.NEXT_PUBLIC_API_BASE ?? process.env.API_BASE
  );
}

async function parseError(res: Response): Promise<never> {
  const text = await res.text();
  let detail = text;
  try {
    const j = JSON.parse(text) as {
      detail?: unknown;
      error?: unknown;
      errors?: unknown;
    };
    if (j.detail !== undefined) {
      detail =
        typeof j.detail === "string"
          ? j.detail
          : JSON.stringify(j.detail, null, 2);
    } else if (j.error !== undefined) {
      detail =
        typeof j.error === "string" ? j.error : JSON.stringify(j.error, null, 2);
    } else if (j.errors !== undefined) {
      detail = JSON.stringify(j.errors, null, 2);
    }
  } catch {
    /* keep text */
  }
  throw new Error(`${res.status} ${res.statusText}: ${detail.slice(0, 800)}`);
}

export async function fetchJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const base = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) await parseError(res);
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return fetchJson<T>(path, { method: "GET", ...init });
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  init?: RequestInit
): Promise<T> {
  return fetchJson<T>(path, {
    ...init,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getGpuMetricsPlaceholder(): Promise<Record<string, unknown>> {
  throw new Error("Not implemented on backend yet");
}

export async function getRequestHistoryPlaceholder(): Promise<unknown[]> {
  throw new Error("Not implemented on backend yet");
}
