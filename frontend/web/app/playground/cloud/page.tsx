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

const AWS_SERVICES = [
  "s3",
  "ec2",
  "lambda",
  "iam",
  "rds",
  "dynamodb",
  "cloudformation",
  "ecs",
  "eks",
  "vpc",
  "cloudwatch",
  "sns",
  "sqs",
  "api-gateway",
  "route53",
  "elasticache",
  "kinesis",
  "glue",
  "athena",
  "redshift",
] as const;

const CLOUD_TIPS = [
  "aws_service is required — pick the AWS service to test (e.g. s3, lambda, iam).",
  "experience_years ≤ 5 defaults to 'code' mode; > 5 defaults to 'scenario' mode.",
  "Override mode explicitly to force code or scenario regardless of experience.",
  "count > 1 streams questions as NDJSON — the proxy collects them into a JSON array.",
  "concepts narrows the question further, e.g. 'presigned URLs', 'lifecycle policies'.",
];

export default function CloudPlaygroundPage() {
  const [awsService, setAwsService]           = useState<string>(AWS_SERVICES[0]);
  const [customService, setCustomService]     = useState("");
  const [useCustomService, setUseCustomService] = useState(false);
  const [jobRole, setJobRole]                 = useState("Cloud Engineer");
  const [experienceYears, setExperienceYears] = useState(2);
  const [difficulty, setDifficulty]           = useState<Difficulty>("Medium");
  const [mode, setMode]                       = useState<Mode | "auto">("auto");
  const [concepts, setConcepts]               = useState("");
  const [count, setCount]                     = useState(1);
  const [timeLimit, setTimeLimit]             = useState(30);

  const [submitting, setSubmitting]           = useState(false);
  const [error, setError]                     = useState<string | null>(null);
  const [result, setResult]                   = useState<unknown>(null);
  const [resultTs, setResultTs]               = useState<number | null>(null);
  const [t0, setT0]                           = useState<number | null>(null);

  const [history, setHistory]                 = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx]         = useState<number | null>(null);

  const resolvedService = useCustomService ? customService.trim().toLowerCase() : awsService;

  const payload = useMemo(() => ({
    aws_service: resolvedService,
    job_role: jobRole.trim(),
    experience_years: Math.max(0, Math.min(50, experienceYears)),
    difficulty,
    ...(mode !== "auto" ? { mode } : {}),
    concepts: concepts.split(",").map((s) => s.trim()).filter(Boolean),
    count: Math.max(1, Math.min(20, count)),
    time_limit: Math.max(5, Math.min(180, timeLimit)),
  }), [resolvedService, jobRole, experienceYears, difficulty, mode, concepts, count, timeLimit]);

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvedService) { setError("aws_service is required"); return; }
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(true);
    setT0(Date.now());
    try {
      // Backend streams NDJSON for count > 1; proxy converts to JSON array.
      const resp = await adminPostJson<unknown>("/api/admin/generate/cloud", payload);
      const ts = Date.now();
      const dur = t0 ? (ts - t0) / 1000 : 0;
      setResult(resp);
      setResultTs(ts);
      setHistory((h) => [{ timestamp: ts, endpoint: "Cloud (AWS)", payload, result: resp, durationSeconds: dur }, ...h].slice(0, 10));
      setSelectedIdx(0);
    } catch (err) {
      setError((err as Error).message || "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }, [payload, resolvedService, t0]);

  const onReset = useCallback(() => {
    setAwsService(AWS_SERVICES[0]);
    setCustomService("");
    setUseCustomService(false);
    setJobRole("Cloud Engineer");
    setExperienceYears(2);
    setDifficulty("Medium");
    setMode("auto");
    setConcepts("");
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
        title="Cloud (AWS) question generation"
        description="Generate AWS cloud questions via /api/v1/generate-cloud-question"
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
        tips={CLOUD_TIPS}
      >
        {/* AWS service */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="AWS service" required>
            {useCustomService ? (
              <TextInput
                value={customService}
                onChange={(e) => setCustomService(e.target.value)}
                placeholder="e.g. step-functions, eventbridge"
                required
              />
            ) : (
              <Select value={awsService} onChange={(e) => setAwsService(e.target.value)}>
                {AWS_SERVICES.map((s) => (
                  <option key={s} value={s}>{s.toUpperCase()}</option>
                ))}
              </Select>
            )}
            <button
              type="button"
              onClick={() => setUseCustomService((v) => !v)}
              className="mt-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {useCustomService ? "← Use preset list" : "Enter custom service →"}
            </button>
          </Field>

          <Field label="Job role">
            <TextInput value={jobRole} onChange={(e) => setJobRole(e.target.value)} placeholder="Cloud Engineer" />
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

        <Field label="Concepts (comma separated)" hint="Optional — e.g. 'presigned URLs, lifecycle policies'">
          <TextInput
            value={concepts}
            onChange={(e) => setConcepts(e.target.value)}
            placeholder="e.g. versioning, cross-region replication"
          />
        </Field>
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard
          endpoint="Cloud (AWS)"
          result={result}
          timestamp={resultTs}
          durationSeconds={t0 ? (resultTs - t0) / 1000 : undefined}
        />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}
