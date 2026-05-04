"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import {
  EndpointFormShell,
  Field,
  Select,
  TextInput,
  DifficultySelector,
} from "@/components/playground/EndpointFormShell";
import { ResponseCard } from "@/components/playground/ResponseCard";
import { RequestHistory, type HistoryItem } from "@/components/playground/RequestHistory";

type Difficulty = "Easy" | "Medium" | "Hard";
type Mode = "code" | "scenario";

const DEVOPS_FOCUS_AREAS = [
  "CI/CD",
  "Docker",
  "Kubernetes",
  "Terraform",
  "Ansible",
  "Jenkins",
  "GitHub Actions",
  "Monitoring & Observability",
  "Linux & Shell Scripting",
  "Networking",
  "Security & Compliance",
  "Site Reliability Engineering",
] as const;

const DEVOPS_TIPS = [
  "focus_area is required — pick the DevOps domain to test.",
  "experience_years ≤ 5 defaults to 'code' mode; > 5 defaults to 'scenario' mode.",
  "Override mode explicitly if you want to force code or scenario regardless of experience.",
  "count > 1 streams questions as NDJSON — the proxy collects them into a JSON array.",
  "topics narrows the question further, e.g. 'blue-green deployment', 'helm charts'.",
];

function hasJobId(v: unknown): v is { job_id: string } {
  return !!v && typeof v === "object" && typeof (v as { job_id?: unknown }).job_id === "string";
}

export default function DevOpsPlaygroundPage() {
  const [focusArea, setFocusArea]           = useState<string>(DEVOPS_FOCUS_AREAS[0]);
  const [customFocus, setCustomFocus]       = useState("");
  const [useCustomFocus, setUseCustomFocus] = useState(false);
  const [jobRole, setJobRole]               = useState("DevOps Engineer");
  const [experienceYears, setExperienceYears] = useState(2);
  const [difficulty, setDifficulty]         = useState<Difficulty>("Medium");
  const [mode, setMode]                     = useState<Mode | "auto">("auto");
  const [topics, setTopics]                 = useState("");
  const [count, setCount]                   = useState(1);
  const [timeLimit, setTimeLimit]           = useState(30);

  const [submitting, setSubmitting]         = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [result, setResult]                 = useState<unknown>(null);
  const [resultTs, setResultTs]             = useState<number | null>(null);
  const [t0, setT0]                         = useState<number | null>(null);

  const [history, setHistory]               = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx]       = useState<number | null>(null);

  const resolvedFocus = useCustomFocus ? customFocus.trim() : focusArea;

  const payload = useMemo(() => ({
    focus_area: resolvedFocus,
    job_role: jobRole.trim(),
    experience_years: Math.max(0, Math.min(50, experienceYears)),
    difficulty,
    ...(mode !== "auto" ? { mode } : {}),
    topics: topics.split(",").map((s) => s.trim()).filter(Boolean),
    count: Math.max(1, Math.min(20, count)),
    time_limit: Math.max(5, Math.min(180, timeLimit)),
  }), [resolvedFocus, jobRole, experienceYears, difficulty, mode, topics, count, timeLimit]);

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvedFocus) { setError("focus_area is required"); return; }
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(true);
    setT0(Date.now());
    try {
      // Backend streams NDJSON for count > 1; proxy converts to JSON array.
      // For count = 1 it returns a plain JSON object — both work fine here.
      const resp = await adminPostJson<unknown>("/api/admin/generate/devops", payload);
      const ts = Date.now();
      const dur = t0 ? (ts - t0) / 1000 : 0;
      setResult(resp);
      setResultTs(ts);
      setHistory((h) => [{ timestamp: ts, endpoint: "DevOps", payload, result: resp, durationSeconds: dur }, ...h].slice(0, 10));
      setSelectedIdx(0);
    } catch (err) {
      setError((err as Error).message || "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }, [payload, resolvedFocus, t0]);

  const onReset = useCallback(() => {
    setFocusArea(DEVOPS_FOCUS_AREAS[0]);
    setCustomFocus("");
    setUseCustomFocus(false);
    setJobRole("DevOps Engineer");
    setExperienceYears(2);
    setDifficulty("Medium");
    setMode("auto");
    setTopics("");
    setCount(1);
    setTimeLimit(30);
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(false);
  }, []);

  return (
    <div className="space-y-4">
      <EndpointFormShell
        title="DevOps question generation"
        description="Generate DevOps / infrastructure questions via /api/v1/generate-devops-question"
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
        tips={DEVOPS_TIPS}
      >
        {/* Focus area */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Focus area" required>
            {useCustomFocus ? (
              <TextInput
                value={customFocus}
                onChange={(e) => setCustomFocus(e.target.value)}
                placeholder="e.g. GitOps, ArgoCD"
                required
              />
            ) : (
              <Select value={focusArea} onChange={(e) => setFocusArea(e.target.value)}>
                {DEVOPS_FOCUS_AREAS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </Select>
            )}
            <button
              type="button"
              onClick={() => setUseCustomFocus((v) => !v)}
              className="mt-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {useCustomFocus ? "← Use preset list" : "Enter custom focus area →"}
            </button>
          </Field>

          <Field label="Job role">
            <TextInput value={jobRole} onChange={(e) => setJobRole(e.target.value)} placeholder="DevOps Engineer" />
          </Field>

          <Field label="Experience years" hint="0–50 — drives auto mode selection">
            <TextInput
              type="number" min={0} max={50} value={experienceYears}
              onChange={(e) => setExperienceYears(Math.max(0, Math.min(50, parseInt(e.target.value || "0", 10))))}
            />
          </Field>

          <Field label="Difficulty">
            <DifficultySelector value={difficulty} onChange={(v) => setDifficulty(v as Difficulty)} />
          </Field>

          <Field label="Mode" hint="auto = derived from experience_years (≤5 → code, >5 → scenario)">
            <Select value={mode} onChange={(e) => setMode(e.target.value as Mode | "auto")}>
              <option value="auto">Auto (from experience)</option>
              <option value="code">Code</option>
              <option value="scenario">Scenario</option>
            </Select>
          </Field>

          <Field label="Count" hint="1–20 questions">
            <TextInput
              type="number" min={1} max={20} value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(20, parseInt(e.target.value || "1", 10))))}
            />
          </Field>

          <Field label="Time limit (minutes)" hint="5–180">
            <TextInput
              type="number" min={5} max={180} value={timeLimit}
              onChange={(e) => setTimeLimit(Math.max(5, Math.min(180, parseInt(e.target.value || "30", 10))))}
            />
          </Field>
        </div>

        <Field label="Topics (comma separated)" hint="Optional — e.g. 'blue-green deployment, helm charts'">
          <TextInput
            value={topics}
            onChange={(e) => setTopics(e.target.value)}
            placeholder="e.g. rolling updates, pod autoscaling"
          />
        </Field>
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard
          endpoint="DevOps"
          result={result}
          timestamp={resultTs}
          durationSeconds={t0 ? (resultTs - t0) / 1000 : undefined}
        />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}
