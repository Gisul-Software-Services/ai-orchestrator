/**
 * Persist playground form + last response in sessionStorage so navigating away
 * (Monitoring, etc.) and back does not lose generated content. Cleared when the tab closes.
 */

import type { EndpointId, PlaygroundFormState } from "./buildPayload";
import type { GenerateMeta } from "./generation";

const STORAGE_KEY = "gisul-model-console-playground-v1";
const MAX_BYTES = 4_500_000; // stay under typical ~5MiB sessionStorage limits

export interface PersistedPlaygroundState {
  v: 1;
  endpoint: EndpointId;
  form: PlaygroundFormState;
  result: unknown | null;
  error: string | null;
  runMeta?: GenerateMeta | null;
  savedAt: string;
}

export function readPlaygroundState(): PersistedPlaygroundState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedPlaygroundState;
    if (parsed?.v !== 1 || !parsed.endpoint || !parsed.form) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writePlaygroundState(state: {
  endpoint: EndpointId;
  form: PlaygroundFormState;
  result: unknown | null;
  error: string | null;
  runMeta?: GenerateMeta | null;
}): void {
  if (typeof window === "undefined") return;
  const payload: PersistedPlaygroundState = {
    v: 1,
    endpoint: state.endpoint,
    form: state.form,
    result: state.result,
    error: state.error,
    runMeta: state.runMeta,
    savedAt: new Date().toISOString(),
  };
  try {
    let raw = JSON.stringify(payload);
    if (raw.length > MAX_BYTES) {
      console.warn(
        "[playground] Response too large for session storage; saving form only."
      );
      raw = JSON.stringify({ ...payload, result: null });
    }
    sessionStorage.setItem(STORAGE_KEY, raw);
  } catch (e) {
    console.warn("[playground] Could not save session state:", e);
  }
}

export function clearPlaygroundState(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
