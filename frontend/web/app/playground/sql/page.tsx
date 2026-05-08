"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import {
  EndpointFormShell,
  Field,
  Select,
  TextInput,
  Toggle,
  DifficultySelector,
} from "@/components/playground/EndpointFormShell";
import { JobPoller } from "@/components/playground/JobPoller";
import { ResponseCard } from "@/components/playground/ResponseCard";
import { RequestHistory, type HistoryItem } from "@/components/playground/RequestHistory";

type Difficulty = "Easy" | "Medium" | "Hard";

const SQL_CATEGORIES = [
  "select",
  "join",
  "aggregation",
  "subquery",
  "window",
  "cte",
  "index",
  "transaction",
  "stored_procedure",
  "trigger",
  "view",
  "normalization",
] as const;

const SQL_TIPS = [
  "Use sql_category to target a specific SQL concept (join, aggregation, window, etc.).",
  "topic is optional — use it to set the domain context (e.g. e-commerce, HR system).",
  "count=1 returns a single JSON object; count>1 streams questions as NDJSON.",
  "The generator auto-routes between RAG catalog and schema-based generation.",
  "Difficulty controls question complexity: Easy → basic syntax, Hard → advanced patterns.",
];

export default function SqlGenerationPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [topic, setTopic] = useState("");
  const [sqlCategory, setSqlCategory] = useState<string>("join");
  const [count, setCount] = useState(1);
  const [useCache, setUseCache] = useState(true);

  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [resultTs, setResultTs] = useState<number | null>(null);
  const [t0, setT0] = useState<number | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const payload = useMemo(() => ({
    difficulty,
    topic: topic.trim() || undefined,
    sql_category: sqlCategory,
    count: Math.max(1, Math.min(20, count)),
    use_cache: useCache,
  }), [difficulty, topic, sqlCategory, count, useCache]);

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setResultTs(null);
    setJobId(null);
    setSubmitting(true);
    setT0(Date.now());
    try {
      const resp = await adminPostJson<{ job_id: string }>(
        "/api/admin/generate/sql-async",
        payload
      );
      setJobId(resp.job_id);
    } catch (err) {
      setError((err as Error).message || "Failed to submit");
      setJobId(null);
      setSubmitting(false);
    }
  }, [payload]);

  const handleComplete = useCallback((res: unknown) => {
    const ts = Date.now();
    const dur = t0 ? (ts - t0) / 1000 : 0;
    setResult(res);
    setResultTs(ts);
    setSubmitting(false);
    setJobId(null);
    setHistory((h) => [{
      timestamp: ts, endpoint: "SQL Generation", payload, result: res,
      durationSeconds: dur,
    }, ...h].slice(0, 10));
    setSelectedIdx(0);
  }, [payload, t0]);

  const handleError = useCallback((msg: string) => {
    setError(msg);
    setSubmitting(false);
    setJobId(null);
  }, []);

  const onReset = useCallback(() => {
    setDifficulty("Medium");
    setTopic("");
    setSqlCategory("join");
    setCount(1);
    setUseCache(true);
    setJobId(null);
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(false);
  }, []);

  return (
    <div className="space-y-4">
      <EndpointFormShell
        title="SQL question generation"
        description="Generate SQL questions via /api/v1/generate-sql-question with intelligent category routing."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
        tips={SQL_TIPS}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Difficulty">
            <DifficultySelector value={difficulty} onChange={(v) => setDifficulty(v as Difficulty)} />
          </Field>
          <Field label="SQL category" hint="The SQL concept to test">
            <Select value={sqlCategory} onChange={(e) => setSqlCategory(e.target.value)}>
              {SQL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Topic / domain" hint="Optional — e.g. e-commerce, HR system">
            <TextInput
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. e-commerce, banking, HR system"
            />
          </Field>
          <Field label="Number of questions" hint="1-20">
            <TextInput
              type="number"
              min={1}
              max={20}
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(20, parseInt(e.target.value || "1", 10))))}
            />
          </Field>
        </div>

        <Toggle checked={useCache} onChange={setUseCache} label="Use cache" description="Return cached result for identical requests" />

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard
          endpoint="SQL Generation"
          result={result}
          timestamp={resultTs}
          durationSeconds={t0 ? (resultTs - t0) / 1000 : undefined}
        />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}
