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

const DSA_LANGUAGE_OPTIONS = [
  "python", "java", "javascript", "typescript",
  "kotlin", "go", "rust", "cpp", "csharp", "c",
] as const;

function hasJobId(v: unknown): v is { job_id: string } {
  return !!v && typeof v === "object" && typeof (v as { job_id?: unknown }).job_id === "string";
}

export default function DsaPlaygroundPage() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [concepts, setConcepts] = useState("");
  const [count, setCount] = useState(1);
  const [languages, setLanguages] = useState<string[]>(["python", "javascript"]);

  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [resultTs, setResultTs] = useState<number | null>(null);
  const [t0, setT0] = useState<number | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const toggleLanguage = useCallback((lang: string) => {
    setLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  }, []);

  const payload = useMemo(() => {
    const conceptsList = concepts
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return {
      topic: topic.trim(),
      difficulty,
      concepts: conceptsList,
      languages,
      count: Math.max(1, Math.min(20, count)),
    };
  }, [topic, difficulty, concepts, languages, count]);

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setResult(null);
      setResultTs(null);
      setSubmitting(true);
      setT0(Date.now());
      try {
        const resp = await adminPostJson<unknown>(
          "/api/admin/generate/dsa",
          payload
        );
        if (hasJobId(resp)) {
          setJobId(resp.job_id);
        } else {
          const ts = Date.now();
          const dur = t0 ? (ts - t0) / 1000 : 0;
          setResult(resp);
          setResultTs(ts);
          setSubmitting(false);
          setJobId(null);
          setHistory((h) => [{ timestamp: ts, endpoint: "DSA", payload, result: resp, durationSeconds: dur }, ...h].slice(0, 10));
          setSelectedIdx(0);
        }
      } catch (err) {
        setError((err as Error).message || "Failed to submit");
        setJobId(null);
        setSubmitting(false);
      }
    },
    [payload, t0]
  );

  const handleComplete = useCallback(
    (res: unknown) => {
      const ts = Date.now();
      const dur = t0 ? (ts - t0) / 1000 : 0;
      setResult(res);
      setResultTs(ts);
      setSubmitting(false);
      setJobId(null);
      setHistory((h) => [{ timestamp: ts, endpoint: "DSA", payload, result: res, durationSeconds: dur }, ...h].slice(0, 10));
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
    setConcepts("");
    setCount(1);
    setLanguages(["python", "javascript"]);
    setJobId(null);
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(false);
  }, []);

  return (
    <div className="space-y-4">
      <EndpointFormShell
        title="DSA question generation"
        description="Generate 1–20 unique DSA questions via bulk RAG retrieval + Qwen reword."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Topic (required)" hint='e.g. "binary search", "dynamic programming"'>
            <TextInput
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              placeholder="e.g. dynamic programming"
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
          <Field label="Concepts (comma separated)" hint="Optional">
            <TextInput
              value={concepts}
              onChange={(e) => setConcepts(e.target.value)}
              placeholder="e.g. memoization, knapsack"
            />
          </Field>
          <Field label="Count" hint="Number of questions (1–20)">
            <TextInput
              type="number"
              value={String(count)}
              onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value))))}
              min={1}
              max={20}
            />
          </Field>
        </div>

        <Field label="Languages" hint="Select at least one">
          <div className="flex flex-wrap gap-2 mt-1">
            {DSA_LANGUAGE_OPTIONS.map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => toggleLanguage(lang)}
                className={`px-3 py-1 rounded text-sm border transition-colors ${
                  languages.includes(lang)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-transparent text-gray-400 border-gray-600 hover:border-gray-400"
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </Field>

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard endpoint="DSA" result={result} timestamp={resultTs} />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}
