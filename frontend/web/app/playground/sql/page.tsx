"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import {
  EndpointFormShell,
  Field,
  Select,
  TextInput,
  Toggle,
} from "@/components/playground/EndpointFormShell";
import { JobPoller } from "@/components/playground/JobPoller";
import { ResponseCard } from "@/components/playground/ResponseCard";
import {
  RequestHistory,
  type HistoryItem,
} from "@/components/playground/RequestHistory";

type Difficulty = "Easy" | "Medium" | "Hard";
type Dialect = "MySQL" | "PostgreSQL" | "SQLite" | "MSSQL";

export default function SqlPlaygroundPage() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [numQuestions, setNumQuestions] = useState(2);
  const [dialect, setDialect] = useState<Dialect>("MySQL");
  const [concepts, setConcepts] = useState("");
  const [useCache, setUseCache] = useState(true);

  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [resultTs, setResultTs] = useState<number | null>(null);
  const [t0, setT0] = useState<number | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const payload = useMemo(() => {
    const conceptsList = concepts
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return {
      topic: topic.trim(),
      difficulty,
      num_questions: Math.max(1, Math.min(5, numQuestions)),
      dialect,
      concepts: conceptsList,
      use_cache: useCache,
      // backend expects database_type + role context
      database_type: dialect,
      job_role: "Data Analyst",
      experience_years: "1-3 (Junior)",
    };
  }, [topic, difficulty, numQuestions, dialect, concepts, useCache]);

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setResult(null);
      setResultTs(null);
      setSubmitting(true);
      setT0(Date.now());
      try {
        const resp = await adminPostJson<{ job_id: string }>(
          "/api/admin/generate/sql",
          payload
        );
        setJobId(resp.job_id);
      } catch (err) {
        setError((err as Error).message || "Failed to submit");
        setJobId(null);
        setSubmitting(false);
      }
    },
    [payload]
  );

  const handleComplete = useCallback(
    (res: unknown) => {
      const ts = Date.now();
      const dur = t0 ? (ts - t0) / 1000 : 0;
      setResult(res);
      setResultTs(ts);
      setSubmitting(false);
      setJobId(null);
      setHistory((h) => [{ timestamp: ts, endpoint: "SQL", payload, result: res, durationSeconds: dur }, ...h].slice(0, 10));
      setSelectedIdx(0);
    },
    [payload, t0]
  );

  const handleError = useCallback((msg: string) => {
    setError(msg);
    setSubmitting(false);
    setJobId(null);
  }, []);

  const onReset = useCallback(() => {
    setTopic("");
    setDifficulty("Medium");
    setNumQuestions(2);
    setDialect("MySQL");
    setConcepts("");
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
        title="SQL problem generation"
        description="Generate SQL questions with schema and expected query."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Topic (required)">
            <TextInput
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              placeholder="e.g. window functions, joins, aggregations"
            />
          </Field>
          <Field label="Difficulty">
            <Select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as Difficulty)}
            >
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </Select>
          </Field>
          <Field label="Number of questions">
            <TextInput
              type="number"
              min={1}
              max={5}
              value={numQuestions}
              onChange={(e) =>
                setNumQuestions(parseInt(e.target.value || "1", 10))
              }
            />
          </Field>
          <Field label="Dialect">
            <Select value={dialect} onChange={(e) => setDialect(e.target.value as Dialect)}>
              <option>MySQL</option>
              <option>PostgreSQL</option>
              <option>SQLite</option>
              <option>MSSQL</option>
            </Select>
          </Field>
          <Field label="Concepts (comma separated)" hint="Optional">
            <TextInput
              value={concepts}
              onChange={(e) => setConcepts(e.target.value)}
              placeholder="e.g. rank, dense_rank, partition by"
            />
          </Field>
        </div>
        <Toggle checked={useCache} onChange={setUseCache} label="Use cache" />

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard endpoint="SQL" result={result} timestamp={resultTs} />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}

