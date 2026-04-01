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

export default function TopicsPlaygroundPage() {
  const [domain, setDomain] = useState("");
  const [numTopics, setNumTopics] = useState(10);
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [useCache, setUseCache] = useState(true);

  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [resultTs, setResultTs] = useState<number | null>(null);
  const [t0, setT0] = useState<number | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  // Backend requires assessment_title/job_designation/skills/experience_*.
  // Map the requested "domain" field into those required fields deterministically.
  const payload = useMemo(() => {
    const d = domain.trim();
    const n = Math.max(1, Math.min(20, numTopics));
    return {
      assessment_title: `${d || "General"} Assessment`,
      job_designation: d || "Generalist",
      skills: d ? [d] : ["General"],
      experience_min: difficulty === "Easy" ? 0 : difficulty === "Medium" ? 1 : 3,
      experience_max: difficulty === "Easy" ? 1 : difficulty === "Medium" ? 3 : 6,
      experience_mode: "corporate",
      num_topics: n,
      num_questions: n,
      use_cache: useCache,
    };
  }, [domain, numTopics, difficulty, useCache]);

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
          "/api/admin/generate/topics",
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
      setHistory((h) => [{ timestamp: ts, endpoint: "Topics", payload, result: res, durationSeconds: dur }, ...h].slice(0, 10));
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
    setDomain("");
    setNumTopics(10);
    setDifficulty("Medium");
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
        title="Topics generation"
        description="Generate a list of assessment topics."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label='Domain (required)' hint='e.g. "Python", "React", "Machine Learning"'>
            <TextInput
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              required
              placeholder="e.g. Machine Learning"
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
          <Field label="Number of topics">
            <TextInput
              type="number"
              min={1}
              max={20}
              value={numTopics}
              onChange={(e) =>
                setNumTopics(parseInt(e.target.value || "1", 10))
              }
            />
          </Field>
        </div>
        <Toggle checked={useCache} onChange={setUseCache} label="Use cache" />

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard endpoint="Topics" result={result} timestamp={resultTs} />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}

