"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import {
  EndpointFormShell,
  Field,
  Select,
  TextArea,
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

export default function DsaEnrichPlaygroundPage() {
  const [problemTitle, setProblemTitle] = useState("");
  const [problemDescription, setProblemDescription] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [languages, setLanguages] = useState(
    "python,java,javascript,typescript,kotlin,go,rust,cpp,csharp,c"
  );
  const [useCache, setUseCache] = useState(true);

  // Critical for this endpoint: input_output drives testcase extraction.
  const [inputOutputJson, setInputOutputJson] = useState("[]");

  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [resultTs, setResultTs] = useState<number | null>(null);
  const [t0, setT0] = useState<number | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const payload = useMemo(() => {
    const langs = languages
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    let input_output: unknown = [];
    try {
      input_output = JSON.parse(inputOutputJson);
    } catch {
      input_output = null;
    }

    return {
      title: problemTitle.trim(),
      difficulty,
      description: problemDescription.trim(),
      languages: langs,
      use_cache: useCache,
      // backend requires input_output list
      input_output,
    };
  }, [problemTitle, problemDescription, difficulty, languages, useCache, inputOutputJson]);

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setResult(null);
      setResultTs(null);
      setSubmitting(true);
      setT0(Date.now());

      // Validate input_output JSON is an array
      try {
        const parsed = JSON.parse(inputOutputJson);
        if (!Array.isArray(parsed)) {
          throw new Error("input_output must be a JSON array");
        }
      } catch (err) {
        setError((err as Error).message || "Invalid input_output JSON");
        setSubmitting(false);
        return;
      }

      try {
        const resp = await adminPostJson<{ job_id: string }>(
          "/api/admin/generate/dsa-enrich",
          payload
        );
        setJobId(resp.job_id);
      } catch (err) {
        setError((err as Error).message || "Failed to submit");
        setSubmitting(false);
      }
    },
    [payload, inputOutputJson, t0]
  );

  const onReset = useCallback(() => {
    setProblemTitle("");
    setProblemDescription("");
    setDifficulty("Medium");
    setLanguages("python,java,javascript,typescript,kotlin,go,rust,cpp,csharp,c");
    setUseCache(true);
    setInputOutputJson("[]");
    setJobId(null);
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(false);
  }, []);

  return (
    <div className="space-y-4">
      <EndpointFormShell
        title="DSA enrichment"
        description="Enrich an existing DSA problem with function signature + multi-language starter code + testcases."
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
      >
        <div className="grid grid-cols-1 gap-4">
          <Field label="Problem title (required)">
            <TextInput
              value={problemTitle}
              onChange={(e) => setProblemTitle(e.target.value)}
              required
              placeholder="e.g. Two Sum"
            />
          </Field>
          <Field label="Problem description (required)">
            <TextArea
              value={problemDescription}
              onChange={(e) => setProblemDescription(e.target.value)}
              required
              placeholder="Paste the full problem statement..."
            />
          </Field>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
            <Field label="Languages (comma separated)" hint="Default is all 10">
              <TextInput
                value={languages}
                onChange={(e) => setLanguages(e.target.value)}
              />
            </Field>
          </div>
          <Field
            label="input_output JSON (required)"
            hint='Must be a JSON array like [{"input":"nums=[2,7,11,15], target=9","output":"[0,1]"}, ...]'
          >
            <TextArea
              value={inputOutputJson}
              onChange={(e) => setInputOutputJson(e.target.value)}
              required
            />
          </Field>
        </div>

        <Toggle checked={useCache} onChange={setUseCache} label="Use cache" />
        <JobPoller
          jobId={jobId}
          onComplete={(res) => {
            const ts = Date.now();
            const dur = t0 ? (ts - t0) / 1000 : 0;
            setResult(res);
            setResultTs(ts);
            setSubmitting(false);
            setJobId(null);
            setHistory((h) =>
              [
                {
                  timestamp: ts,
                  endpoint: "DSA enrich",
                  payload,
                  result: res,
                  durationSeconds: dur,
                },
                ...h,
              ].slice(0, 10)
            );
            setSelectedIdx(0);
          }}
          onError={(msg) => {
            setError(msg);
            setSubmitting(false);
            setJobId(null);
          }}
        />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard endpoint="DSA enrich" result={result} timestamp={resultTs} />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}

