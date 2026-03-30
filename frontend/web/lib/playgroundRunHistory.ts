import type { EndpointId, PlaygroundFormState } from "./buildPayload";

const KEY = "gisul-playground-run-history-v1";
const MAX = 8;

export interface RunHistoryEntry {
  id: string;
  at: string;
  endpoint: EndpointId;
  durationMs: number;
  postUrl: string;
  jobId?: string;
  result: unknown | null;
  error: string | null;
  /** Snapshot of form for context */
  formSummary: string;
}

function read(): RunHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as RunHistoryEntry[];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list: RunHistoryEntry[]) {
  if (typeof window === "undefined") return;
  try {
    let raw = JSON.stringify(list.slice(0, MAX));
    if (raw.length > 3_000_000) {
      raw = JSON.stringify(
        list.map((e) =>
          e.result != null && JSON.stringify(e.result).length > 500_000
            ? { ...e, result: null }
            : e
        )
      );
    }
    sessionStorage.setItem(KEY, raw);
  } catch {
    try {
      sessionStorage.setItem(
        KEY,
        JSON.stringify(
          list.map((e) => ({ ...e, result: null }))
        )
      );
    } catch {
      /* ignore */
    }
  }
}

export function listRunHistory(): RunHistoryEntry[] {
  return read();
}

export function appendRun(entry: Omit<RunHistoryEntry, "id" | "at">): RunHistoryEntry {
  const full: RunHistoryEntry = {
    ...entry,
    id: typeof crypto !== "undefined" ? crypto.randomUUID() : String(Date.now()),
    at: new Date().toISOString(),
  };
  write([full, ...read()].slice(0, MAX));
  return full;
}

export function formSummaryLine(endpoint: EndpointId, form: PlaygroundFormState): string {
  const bits = [endpoint, form.topic?.slice(0, 40) || "—"];
  if (form.difficulty) bits.push(form.difficulty);
  return bits.join(" · ");
}
