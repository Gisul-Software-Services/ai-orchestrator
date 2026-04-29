"use client";

import { useCallback, useMemo, useState } from "react";
import { adminPostJson } from "@/lib/adminApi";
import {
  EndpointFormShell,
  Field,
  TextInput,
  TextArea,
  Toggle,
  DifficultySelector,
} from "@/components/playground/EndpointFormShell";
import { JobPoller } from "@/components/playground/JobPoller";
import { ResponseCard } from "@/components/playground/ResponseCard";
import { RequestHistory, type HistoryItem } from "@/components/playground/RequestHistory";

type Difficulty = "easy" | "medium" | "hard";

const SQL_TIPS = [
  "Paste the candidate's SQL query in the user_query field.",
  "The reference_query is used for context only — never returned to the candidate.",
  "passed=true enforces a score floor of 80%; passed=false caps at 50%.",
  "Include table schemas so the evaluator understands the data model.",
  "Use order_sensitive=true for queries where row order matters.",
  "Evaluation runs async — a job is queued so concurrent requests don't get rate-limited.",
];

export default function SqlEvaluationPage() {
  // Core fields
  const [questionId, setQuestionId]           = useState("q-sql-001");
  const [questionDesc, setQuestionDesc]       = useState("");
  const [userQuery, setUserQuery]             = useState("");
  const [referenceQuery, setReferenceQuery]   = useState("");
  const [maxMarks, setMaxMarks]               = useState(10);
  const [schemas, setSchemas]                 = useState("{}");
  const [difficulty, setDifficulty]           = useState<Difficulty>("medium");
  const [section, setSection]                 = useState("");
  const [orderSensitive, setOrderSensitive]   = useState(false);
  const [useCache, setUseCache]               = useState(true);

  // Test result
  const [passed, setPassed]                   = useState(false);
  const [userOutput, setUserOutput]           = useState("");
  const [expectedOutput, setExpectedOutput]   = useState("");
  const [execError, setExecError]             = useState("");

  const [jobId, setJobId]                     = useState<string | null>(null);
  const [submitting, setSubmitting]           = useState(false);
  const [error, setError]                     = useState<string | null>(null);
  const [result, setResult]                   = useState<unknown>(null);
  const [resultTs, setResultTs]               = useState<number | null>(null);
  const [t0, setT0]                           = useState<number | null>(null);

  const [history, setHistory]                 = useState<HistoryItem[]>([]);
  const [selectedIdx, setSelectedIdx]         = useState<number | null>(null);

  // Parse schemas safely
  const parsedSchemas = useMemo(() => {
    try { return JSON.parse(schemas); } catch { return {}; }
  }, [schemas]);

  const payload = useMemo(() => ({
    question_id: questionId.trim(),
    question_description: questionDesc.trim(),
    user_query: userQuery.trim(),
    reference_query: referenceQuery.trim(),
    max_marks: Math.max(1, maxMarks),
    schemas: parsedSchemas,
    difficulty,
    section: section.trim(),
    order_sensitive: orderSensitive,
    use_cache: useCache,
    test_result: {
      passed,
      user_output: userOutput.trim(),
      expected_output: expectedOutput.trim(),
      error: execError.trim() || null,
    },
  }), [questionId, questionDesc, userQuery, referenceQuery, maxMarks, parsedSchemas,
      difficulty, section, orderSensitive, useCache, passed, userOutput, expectedOutput, execError]);

  const onSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setResultTs(null);
    setJobId(null);
    setSubmitting(true);
    setT0(Date.now());
    try {
      // Use async endpoint — queues the LLM call to avoid 429s under concurrency
      const resp = await adminPostJson<{ job_id: string }>(
        "/api/admin/evaluate/sql-async",
        payload
      );
      setJobId(resp.job_id);
    } catch (err) {
      setError((err as Error).message || "Failed to submit");
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
      timestamp: ts, endpoint: "SQL Evaluation", payload, result: res,
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
    setQuestionId("q-sql-001");
    setQuestionDesc("");
    setUserQuery("");
    setReferenceQuery("");
    setMaxMarks(10);
    setSchemas("{}");
    setDifficulty("medium");
    setSection("");
    setOrderSensitive(false);
    setUseCache(true);
    setPassed(false);
    setUserOutput("");
    setExpectedOutput("");
    setExecError("");
    setJobId(null);
    setError(null);
    setResult(null);
    setResultTs(null);
    setSubmitting(false);
  }, []);

  return (
    <div className="space-y-4">
      <EndpointFormShell
        title="SQL Evaluation"
        description="AI-powered scoring and feedback for candidate SQL submissions via /api/v1/evaluation/sql/async"
        submitting={submitting}
        error={error}
        onSubmit={onSubmit}
        onReset={onReset}
        tips={SQL_TIPS}
      >
        {/* Question context */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Question ID" required>
            <TextInput value={questionId} onChange={(e) => setQuestionId(e.target.value)} required placeholder="q-sql-001" />
          </Field>
          <Field label="Max marks" required>
            <TextInput type="number" min={1} max={100} value={maxMarks}
              onChange={(e) => setMaxMarks(Math.max(1, parseInt(e.target.value || "1", 10)))} />
          </Field>
          <Field label="Difficulty">
            <DifficultySelector value={difficulty} onChange={(v) => setDifficulty(v.toLowerCase() as Difficulty)} />
          </Field>
          <Field label="Section" hint="Optional — e.g. 'SQL Basics'">
            <TextInput value={section} onChange={(e) => setSection(e.target.value)} placeholder="e.g. SQL Basics" />
          </Field>
        </div>

        <Field label="Question description" required>
          <TextArea value={questionDesc} onChange={(e) => setQuestionDesc(e.target.value)} required
            placeholder="Describe the SQL problem the candidate was asked to solve..." />
        </Field>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Candidate query (user_query)" required>
            <TextArea value={userQuery} onChange={(e) => setUserQuery(e.target.value)} required
              placeholder="SELECT * FROM orders WHERE ..." />
          </Field>
          <Field label="Reference query" required hint="Used for context only — never returned">
            <TextArea value={referenceQuery} onChange={(e) => setReferenceQuery(e.target.value)} required
              placeholder="SELECT id, total FROM orders WHERE status = 'completed' ..." />
          </Field>
        </div>

        <Field label="Table schemas (JSON)" hint='e.g. {"orders": {"id": "INT", "total": "DECIMAL"}}'>
          <TextArea value={schemas} onChange={(e) => setSchemas(e.target.value)}
            placeholder='{"orders": {"id": "INT", "status": "VARCHAR", "total": "DECIMAL"}}' />
        </Field>

        {/* Execution result */}
        <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/30 p-4 space-y-4">
          <div className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Execution result (from test runner)</div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-400">Test passed?</span>
            <div className="flex gap-2">
              {[true, false].map((v) => (
                <button key={String(v)} type="button" onClick={() => setPassed(v)}
                  className={`rounded-xl border px-4 py-1.5 text-xs font-semibold transition-all ${
                    passed === v
                      ? v ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                           : "border-red-500 bg-red-500/20 text-red-300"
                      : "border-zinc-700/60 bg-zinc-900/40 text-zinc-500 hover:border-zinc-600"
                  }`}>
                  {v ? "✓ Passed" : "✗ Failed"}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="User output" hint="JSON string of candidate's result rows">
              <TextArea value={userOutput} onChange={(e) => setUserOutput(e.target.value)}
                placeholder='[{"id": 1, "total": 99.99}]' />
            </Field>
            <Field label="Expected output" hint="JSON string of expected result rows">
              <TextArea value={expectedOutput} onChange={(e) => setExpectedOutput(e.target.value)}
                placeholder='[{"id": 1, "total": 99.99}]' />
            </Field>
          </div>

          <Field label="Execution error" hint="Leave empty if no error">
            <TextInput value={execError} onChange={(e) => setExecError(e.target.value)}
              placeholder="e.g. syntax error at or near 'FORM'" />
          </Field>
        </div>

        <div className="flex flex-wrap gap-4">
          <Toggle checked={orderSensitive} onChange={setOrderSensitive}
            label="Order sensitive" description="Row order matters for correctness" />
          <Toggle checked={useCache} onChange={setUseCache}
            label="Use cache" description="Return cached result for identical queries" />
        </div>

        <JobPoller jobId={jobId} onComplete={handleComplete} onError={handleError} />
      </EndpointFormShell>

      {result && resultTs ? (
        <ResponseCard endpoint="SQL Evaluation" result={result} timestamp={resultTs}
          durationSeconds={t0 ? (resultTs - t0) / 1000 : undefined} />
      ) : null}

      <RequestHistory items={history} selectedIndex={selectedIdx} onSelect={setSelectedIdx} />
    </div>
  );
}
