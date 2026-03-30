import type { EndpointId, PlaygroundFormState } from "./buildPayload";

const KEY = "gisul-playground-presets-v1";
const MAX = 24;

export interface PlaygroundPreset {
  id: string;
  name: string;
  endpoint: EndpointId;
  form: PlaygroundFormState;
  savedAt: string;
}

function readAll(): PlaygroundPreset[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as PlaygroundPreset[];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function writeAll(list: PlaygroundPreset[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch {
    /* quota */
  }
}

export function listPresets(): PlaygroundPreset[] {
  return readAll().sort(
    (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime()
  );
}

export function savePreset(
  name: string,
  endpoint: EndpointId,
  form: PlaygroundFormState
): PlaygroundPreset {
  const preset: PlaygroundPreset = {
    id: typeof crypto !== "undefined" ? crypto.randomUUID() : String(Date.now()),
    name: name.trim() || "Untitled",
    endpoint,
    form: { ...form },
    savedAt: new Date().toISOString(),
  };
  const all = readAll().filter((p) => p.name !== preset.name);
  writeAll([preset, ...all]);
  return preset;
}

export function deletePreset(id: string) {
  writeAll(readAll().filter((p) => p.id !== id));
}
