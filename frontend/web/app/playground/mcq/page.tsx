"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import { EndpointFormShell, Field, Select, TextInput, Toggle } from "@/components/playground/EndpointFormShell";
import { JobPoller } from "@/components/playground/JobPoller";
import { ResponseCard } from "@/components/playground/ResponseCard";
import { RequestHistory, type HistoryItem } from "@/components/playground/RequestHistory";

type Difficulty = "Easy" | "Medium" | "Hard";

export default function McqPlaygroundPage() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [numQuestions, setNumQuestions] = useState(3);
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
      num_questions: Math.max(1, Math.min(10, numQuestions)),
      concepts: conceptsList,
      use_cache: useCache,
    };
  }, [topic, difficulty, numQuestions, concepts, useCache]);

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setResult(null);
      setResultTs(null);
      setSubmitting(true);
      setT0(Date.now());
      try {
        const resp = await adminPostJson<{ job_id: string }>("/api/admin/generate/mcq", payload);
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
      setHistory((h) => {
        const next = [
          { timestamp: ts, endpoint: "MCQ", payload, result: res, durationSeconds: dur },
          ...h,
        ];
        return next.slice(0, 10);
      });
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
    setNumQuestions(3);
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
        title="MCQ generation"
        description="Generate multiple choice questions for a topic."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Topic (required)">
            <TextInput value={topic} onChange={(e) => setTopic(e.target.value)} required placeholder="e.g. Python slicing output prediction" />
          </Field>
          <Field label="Difficulty">
            <Select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </Select>
          </Field>
          <Field label="Number of questions">
            <TextInput
              type="number"
              min={1}
              max={10}
              value={numQuestions}
              onChange={(e) => setNumQuestions(parseInt(e.target.value || "1", 10))}
            />
          </Field>
          <Field label="Concepts (comma separated)" hint="Optional">
            <TextInput value={concepts} onChange={(e) => setConcepts(e.target.value)} placeholder="e.g. arrays, pointers, time complexity" />
          </Field>
        </div>
        <Toggle checked={useCache} onChange={setUseCache} label="Use cache" />

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? <ResponseCard endpoint="MCQ" result={result} timestamp={resultTs} /> : null}

      <RequestHistory
        items={history}
        selectedIndex={selectedIdx}
        onSelect={(idx) => setSelectedIdx(idx)}
      />
    </div>
  );
}

