"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  BookmarkPlus,
  FlaskConical,
  Keyboard,
  Link2,
  Trash2,
  History,
} from "lucide-react";
import { API_ENDPOINTS } from "@/lib/endpoints";
import { getApiBaseUrl } from "@/lib/api";
import {
  buildPayload,
  DEFAULT_FORM,
  effectivePlaygroundOrgId,
  mergeOrgIdIntoBody,
  parseEnrichDsaBody,
  type EndpointId,
  type PlaygroundFormState,
} from "@/lib/buildPayload";
import {
  postClearCache,
  postGenerateOrJob,
  getHealthUrl,
  getStatsUrl,
  type GenerateMeta,
} from "@/lib/generation";
import {
  buildPlaygroundShareSearchParams,
  hydrateFormFromSearchParams,
} from "@/lib/playgroundShare";
import {
  appendRun,
  formSummaryLine,
  listRunHistory,
} from "@/lib/playgroundRunHistory";
import { deletePreset, listPresets, savePreset } from "@/lib/playgroundPresets";
import { validatePlaygroundForm } from "@/lib/playgroundValidation";
import { ResponseView } from "./ResponseView";
import { Button } from "@/components/ui/button";
import { readPlaygroundState, writePlaygroundState } from "@/lib/playgroundStorage";

const LABELS: Record<string, string> = {
  "generate-topics": "📋 Generate Topics",
  "generate-mcq": "✅ Multiple Choice (MCQ)",
  "generate-subjective": "✍️ Subjective Questions",
  "generate-coding": "💻 Coding Problems",
  "generate-sql": "🗄️ SQL Problems",
  "generate-aiml": "🤖 AI/ML Synthetic",
  "generate-aiml-library": "📚 AI/ML Library Dataset",
  "generate-dsa-question": "🔢 DSA Question (FAISS RAG)",
  "enrich-dsa": "🔧 Enrich DSA (JSON body)",
};

const IMPLEMENTED = API_ENDPOINTS.filter((e) => e.implemented);

export function PlaygroundClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const q = searchParams.get("endpoint");
  const initialEndpoint = IMPLEMENTED.some((e) => e.id === q)
    ? (q as EndpointId)
    : "generate-aiml-library";

  const [endpoint, setEndpoint] = useState<EndpointId>(initialEndpoint);
  const [form, setForm] = useState<PlaygroundFormState>(DEFAULT_FORM);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pollHint, setPollHint] = useState<string | null>(null);
  const [sideMsg, setSideMsg] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [runMeta, setRunMeta] = useState<GenerateMeta | null>(null);
  const [historyRev, setHistoryRev] = useState(0);
  const [presetName, setPresetName] = useState("");
  const [shareFlash, setShareFlash] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);

  const apiBaseDisplay = useMemo(() => getApiBaseUrl().replace(/\/$/, ""), []);
  const effectiveOrgId = useMemo(
    () => effectivePlaygroundOrgId(form),
    [form]
  );
  // Avoid hydration mismatch: SSR has no storage; first paint must match SSR (empty) until useLayoutEffect runs.
  const runHistory = useMemo(
    () => (bootstrapped ? listRunHistory() : []),
    [historyRev, bootstrapped]
  );
  const presets = useMemo(
    () => (bootstrapped ? listPresets() : []),
    [historyRev, bootstrapped]
  );

  const pathSuffix = useMemo(() => {
    if (endpoint === "enrich-dsa") return "enrich-dsa";
    return endpoint;
  }, [endpoint]);

  const setField = useCallback(
    <K extends keyof PlaygroundFormState>(key: K, value: PlaygroundFormState[K]) => {
      setForm((f) => ({ ...f, [key]: value }));
    },
    []
  );

  useLayoutEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const raw = sp.get("endpoint");
    const urlEp =
      raw && IMPLEMENTED.some((e) => e.id === raw) ? (raw as EndpointId) : null;
    const persisted = readPlaygroundState();
    const baseForm: PlaygroundFormState = {
      ...DEFAULT_FORM,
      ...(persisted?.form ?? {}),
    };
    setForm(hydrateFormFromSearchParams(sp, baseForm));

    if (persisted) {
      if (urlEp != null) {
        setEndpoint(urlEp);
        if (urlEp !== persisted.endpoint) {
          setResult(null);
          setError(null);
          setRunMeta(null);
        } else {
          setResult(persisted.result);
          setError(persisted.error);
          setRunMeta(persisted.runMeta ?? null);
        }
      } else {
        setEndpoint(persisted.endpoint);
        setResult(persisted.result);
        setError(persisted.error);
        setRunMeta(persisted.runMeta ?? null);
        const cur = sp.get("endpoint");
        if (cur !== persisted.endpoint) {
          router.replace(
            `/playground?endpoint=${encodeURIComponent(persisted.endpoint)}`
          );
        }
      }
    } else if (urlEp != null) {
      setEndpoint(urlEp);
      setRunMeta(null);
    } else {
      setRunMeta(null);
    }

    setBootstrapped(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-time bootstrap; router is stable
  }, []);

  useEffect(() => {
    if (!bootstrapped) return;
    writePlaygroundState({ endpoint, form, result, error, runMeta });
  }, [bootstrapped, endpoint, form, result, error, runMeta]);

  useEffect(() => {
    if (!loading) {
      setElapsedMs(0);
      return;
    }
    const t0 = performance.now();
    setElapsedMs(0);
    const id = window.setInterval(() => {
      setElapsedMs(Math.round(performance.now() - t0));
    }, 250);
    return () => clearInterval(id);
  }, [loading]);

  useEffect(() => {
    if (!bootstrapped) return;
    if (!q || !IMPLEMENTED.some((e) => e.id === q)) return;
    if (q === endpoint) return;
    setEndpoint(q as EndpointId);
    setResult(null);
    setError(null);
    setRunMeta(null);
  }, [q, bootstrapped, endpoint]);

  const copyShareLink = useCallback(async () => {
    const qs = buildPlaygroundShareSearchParams(endpoint, form);
    const path = `/playground?${qs}`;
    const url =
      typeof window !== "undefined"
        ? `${window.location.origin}${path}`
        : path;
    try {
      await navigator.clipboard.writeText(url);
      setShareFlash(true);
      setTimeout(() => setShareFlash(false), 2000);
    } catch {
      /* ignore */
    }
  }, [endpoint, form]);

  const onSubmit = useCallback(async () => {
    const errs = validatePlaygroundForm(endpoint, form);
    if (errs.length > 0) {
      setValidationErrors(errs);
      return;
    }
    setValidationErrors([]);
    setError(null);
    setResult(null);
    setRunMeta(null);
    setPollHint(null);
    setLoading(true);
    const tSubmit = performance.now();
    const headers: Record<string, string> = {
      "X-Request-Id": crypto.randomUUID(),
    };
    const org = effectivePlaygroundOrgId(form);
    if (org) headers["X-Org-Id"] = org;

    try {
      let body: Record<string, unknown>;
      if (endpoint === "enrich-dsa") {
        body = mergeOrgIdIntoBody(
          form,
          parseEnrichDsaBody(form.enrichDsaJson)
        );
      } else {
        body = buildPayload(endpoint, form);
      }

      const { result: out, meta } = await postGenerateOrJob(pathSuffix, body, {
        headers,
        onProgress: (msg) => setPollHint(msg),
      });
      setResult(out);
      setRunMeta(meta);
      appendRun({
        endpoint,
        durationMs: meta.durationMs,
        postUrl: meta.postUrl,
        jobId: meta.jobId,
        result: out,
        error: null,
        formSummary: formSummaryLine(endpoint, form),
      });
      setHistoryRev((n) => n + 1);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setRunMeta(null);
      appendRun({
        endpoint,
        durationMs: Math.round(performance.now() - tSubmit),
        postUrl: `${getApiBaseUrl().replace(/\/$/, "")}/api/v1/${pathSuffix}`,
        result: null,
        error: msg,
        formSummary: formSummaryLine(endpoint, form),
      });
      setHistoryRev((n) => n + 1);
    } finally {
      setLoading(false);
      setPollHint(null);
    }
  }, [endpoint, form, pathSuffix]);

  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!loading) void onSubmit();
      }
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [loading, onSubmit]);

  const health = async () => {
    setSideMsg(null);
    try {
      const r = await fetch(getHealthUrl());
      if (!r.ok) throw new Error(await r.text());
      const h = (await r.json()) as Record<string, unknown>;
      setSideMsg(
        `Health: ${String(h.status)} | model: ${h.model_loaded ? "ok" : "no"} | active jobs: ${String(h.active_jobs ?? "")}`
      );
    } catch (e) {
      setSideMsg(e instanceof Error ? e.message : "Health check failed");
    }
  };

  const stats = async () => {
    setSideMsg(null);
    try {
      const r = await fetch(getStatsUrl());
      if (!r.ok) throw new Error(await r.text());
      const s = (await r.json()) as Record<string, unknown>;
      setSideMsg(
        `Requests: ${String(s.total_requests)} | cache hit %: ${String(s.cache_hit_rate_percent)}`
      );
    } catch (e) {
      setSideMsg(e instanceof Error ? e.message : "Stats failed");
    }
  };

  const clearCache = async () => {
    setSideMsg(null);
    try {
      await postClearCache();
      setSideMsg("Cache cleared.");
    } catch (e) {
      setSideMsg(e instanceof Error ? e.message : "Clear cache failed");
    }
  };

  const needsTopicBlock = [
    "generate-mcq",
    "generate-subjective",
    "generate-coding",
    "generate-sql",
    "generate-aiml",
    "generate-aiml-library",
    "generate-dsa-question",
  ].includes(endpoint);

  const needsTopicsFields = endpoint === "generate-topics";
  const needsAudience = ["generate-mcq", "generate-subjective"].includes(endpoint);
  const needsLanguage = endpoint === "generate-coding";
  const needsDb = endpoint === "generate-sql";
  const needsJobMeta = ["generate-coding", "generate-sql"].includes(endpoint);
  const needsConcepts = ["generate-aiml-library", "generate-dsa-question"].includes(
    endpoint
  );
  const needsDsaLangs = endpoint === "generate-dsa-question";
  const showNumQuestions = ![
    "generate-aiml",
    "generate-aiml-library",
    "generate-dsa-question",
    "enrich-dsa",
  ].includes(endpoint);

  return (
    <div
      className={`mx-auto max-w-5xl space-y-8 ${!bootstrapped ? "opacity-0" : "opacity-100"} transition-opacity duration-150`}
    >
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-console-accent">
          <FlaskConical className="h-7 w-7" strokeWidth={1.5} />
          <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
            Playground
          </h1>
        </div>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
          Call generation endpoints with structured forms and job polling. Your last
          response and fields are kept for this browser tab until you close it or clear
          output.
        </p>
        <p className="flex flex-wrap items-center gap-1.5 text-xs text-zinc-500">
          <Keyboard className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
          <span>
            Submit with <kbd className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-px font-mono text-zinc-400">Ctrl</kbd>{" "}
            + <kbd className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-px font-mono text-zinc-400">Enter</kbd>
          </span>
        </p>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="rounded-full border border-zinc-700/80 bg-zinc-900/60 px-2.5 py-0.5 font-mono text-[10px] text-zinc-400">
            API {apiBaseDisplay}
          </span>
          {effectiveOrgId ? (
            <span className="rounded-full border border-emerald-900/50 bg-emerald-950/30 px-2 py-0.5 text-[10px] text-emerald-300/90">
              org_id + X-Org-Id
            </span>
          ) : (
            <span
              className="rounded-full border border-amber-900/40 bg-amber-950/20 px-2 py-0.5 text-[10px] text-amber-200/90"
              title="Set the field or NEXT_PUBLIC_PLAYGROUND_ORG_ID in .env.local"
            >
              Org ID required
            </span>
          )}
        </div>
        {!effectiveOrgId && (
          <div
            className="rounded-lg border border-amber-900/50 bg-amber-950/25 px-4 py-3 text-sm text-amber-100/95"
            role="alert"
          >
            <p className="font-medium text-amber-200">Organization ID required</p>
            <p className="mt-1 text-xs leading-relaxed text-amber-100/85">
              Enter an Org ID below or set{" "}
              <code className="text-amber-200/90">NEXT_PUBLIC_PLAYGROUND_ORG_ID</code> in{" "}
              <code className="text-amber-200/90">.env.local</code> (rebuild the dev server after
              changing public env vars). In production, pair with API{" "}
              <code className="text-amber-200/90">REQUIRE_VERIFIED_ORG_FOR_GENERATION=true</code> so
              only IDs in <code className="text-amber-200/90">organization_db</code> can call
              generation and catalog preview.
            </p>
          </div>
        )}
        {effectiveOrgId ? (
          <p className="text-xs text-zinc-500">
            <Link
              href={`/usage?org=${encodeURIComponent(effectiveOrgId)}`}
              className="text-console-accent hover:underline"
            >
              Organization usage &amp; logs →
            </Link>
            <span className="text-zinc-600"> · {effectiveOrgId}</span>
          </p>
        ) : null}
      </header>

      <div className="flex flex-col gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-4 shadow-panel sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => health()}>
            Check health
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => stats()}>
            View stats
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => clearCache()}>
            Clear cache
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void copyShareLink()}
            className={shareFlash ? "border-emerald-700 text-emerald-300" : ""}
          >
            <Link2 className="mr-1.5 h-3.5 w-3.5" strokeWidth={2} />
            {shareFlash ? "Link copied" : "Copy share link"}
          </Button>
          {(result !== null || error) && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="border-zinc-600 text-zinc-300 hover:bg-zinc-800"
              onClick={() => {
                setResult(null);
                setError(null);
                setRunMeta(null);
                setValidationErrors([]);
                writePlaygroundState({
                  endpoint,
                  form,
                  result: null,
                  error: null,
                  runMeta: null,
                });
              }}
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5" strokeWidth={2} />
              Clear output
            </Button>
          )}
        </div>
        {sideMsg && (
          <p className="text-xs text-zinc-400 sm:max-w-md sm:text-right">{sideMsg}</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/20 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-300">
            <BookmarkPlus className="h-4 w-4 text-console-accent" strokeWidth={2} />
            Presets
          </div>
          <p className="mb-2 text-xs text-zinc-500">
            Saved in <code className="text-zinc-400">localStorage</code> (this browser).
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              placeholder="Preset name"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-sm"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={() => {
                savePreset(presetName, endpoint, form);
                setPresetName("");
                setHistoryRev((n) => n + 1);
              }}
            >
              Save
            </Button>
          </div>
          {presets.length > 0 && (
            <ul className="mt-3 max-h-36 space-y-1 overflow-y-auto text-xs">
              {presets.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-zinc-800/60 bg-zinc-950/40 px-2 py-1"
                >
                  <span className="truncate text-zinc-400">{p.name}</span>
                  <span className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      className="rounded px-1.5 py-0.5 text-console-accent hover:bg-zinc-800"
                      onClick={() => {
                        setEndpoint(p.endpoint);
                        setForm({ ...p.form });
                        router.replace(
                          `/playground?endpoint=${encodeURIComponent(p.endpoint)}`
                        );
                        setResult(null);
                        setError(null);
                        setRunMeta(null);
                        setValidationErrors([]);
                      }}
                    >
                      Load
                    </button>
                    <button
                      type="button"
                      className="rounded px-1.5 py-0.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"
                      onClick={() => {
                        deletePreset(p.id);
                        setHistoryRev((n) => n + 1);
                      }}
                    >
                      Delete
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/20 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-300">
            <History className="h-4 w-4 text-console-accent" strokeWidth={2} />
            Recent runs
          </div>
          <p className="mb-2 text-xs text-zinc-500">
            Last {runHistory.length} in this tab — click to restore output.
          </p>
          {runHistory.length === 0 ? (
            <p className="text-xs text-zinc-600">No runs yet.</p>
          ) : (
            <ul className="max-h-36 space-y-1 overflow-y-auto text-xs">
              {runHistory.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="w-full rounded-md border border-zinc-800/60 bg-zinc-950/40 px-2 py-1.5 text-left text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50"
                    onClick={() => {
                      setEndpoint(r.endpoint);
                      setResult(r.result);
                      setError(r.error);
                      setRunMeta({
                        durationMs: r.durationMs,
                        postUrl: r.postUrl,
                        jobId: r.jobId,
                      });
                      router.replace(
                        `/playground?endpoint=${encodeURIComponent(r.endpoint)}`
                      );
                    }}
                  >
                    <span className="block truncate font-medium text-zinc-300">
                      {r.error ? "Error" : "OK"} · {Math.round(r.durationMs)}ms
                    </span>
                    <span className="block truncate text-zinc-600">{r.formSummary}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/20 p-4">
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Endpoint
            </label>
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 ring-console-accent/30 focus:outline-none focus:ring-2"
              value={endpoint}
              onChange={(e) => {
                const v = e.target.value as EndpointId;
                setEndpoint(v);
                router.replace(`/playground?endpoint=${encodeURIComponent(v)}`);
                setResult(null);
                setError(null);
                setRunMeta(null);
                setValidationErrors([]);
                if (v === "generate-dsa-question") {
                  setForm((f) => ({
                    ...f,
                    topic: "Arrays and Hash Maps",
                    concepts: "binary search, two pointers",
                  }));
                }
                if (v === "generate-aiml-library") {
                  setForm((f) => ({
                    ...f,
                    topic: "iris",
                    concepts: "classification",
                  }));
                }
              }}
            >
              {IMPLEMENTED.map((e) => (
                <option key={e.id} value={e.id}>
                  {LABELS[e.id] ?? e.label}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/20 p-4">
            <label className="mb-2 block text-sm font-medium text-zinc-300">
              Organization ID
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-400 ring-console-accent/30 focus:outline-none focus:ring-2"
              placeholder="org_id in JSON body + X-Org-Id (or use env default below)"
              value={form.orgId}
              onChange={(e) => setField("orgId", e.target.value)}
              autoComplete="off"
            />
            <p className="mt-1.5 text-xs text-zinc-500">
              Required for generation and per-org usage. If empty, the value from{" "}
              <code className="rounded bg-zinc-900 px-1 text-zinc-400">
                NEXT_PUBLIC_PLAYGROUND_ORG_ID
              </code>{" "}
              (set at build time) is used.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="use_cache"
              checked={form.useCache}
              onChange={(e) => setField("useCache", e.target.checked)}
              disabled={endpoint === "enrich-dsa" || endpoint === "generate-dsa-question"}
            />
            <label htmlFor="use_cache" className="text-sm text-zinc-300">
              Use cache
            </label>
          </div>

          <section className="space-y-4 rounded-xl border border-zinc-800/80 bg-zinc-900/15 p-4">
            <h2 className="text-sm font-semibold text-zinc-200">Request parameters</h2>

            {showNumQuestions && (
              <div>
                <label className="mb-1 block text-xs text-zinc-500">
                  Number of questions / items
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  className="w-32 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                  value={form.numQuestions}
                  onChange={(e) =>
                    setField("numQuestions", Number(e.target.value) || 1)
                  }
                />
              </div>
            )}

            {needsTopicsFields && (
              <div className="grid gap-3 md:grid-cols-2">
                <Field
                  label="Assessment title"
                  value={form.assessmentTitle}
                  onChange={(v) => setField("assessmentTitle", v)}
                />
                <Field
                  label="Job designation"
                  value={form.jobDesignation}
                  onChange={(v) => setField("jobDesignation", v)}
                />
                <Field
                  label="Skills (comma separated)"
                  value={form.skills}
                  onChange={(v) => setField("skills", v)}
                />
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500">
                      Min experience (yrs)
                    </label>
                    <input
                      type="number"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm"
                      value={form.experienceMin}
                      onChange={(e) =>
                        setField("experienceMin", Number(e.target.value))
                      }
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500">
                      Max experience (yrs)
                    </label>
                    <input
                      type="number"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 py-2 text-sm"
                      value={form.experienceMax}
                      onChange={(e) =>
                        setField("experienceMax", Number(e.target.value))
                      }
                    />
                  </div>
                </div>
              </div>
            )}

            {needsTopicBlock && (
              <div className="grid gap-3 md:grid-cols-2">
                <Field
                  label="Topic"
                  value={form.topic}
                  onChange={(v) => setField("topic", v)}
                  placeholder="e.g. iris, customer churn, sentiment analysis"
                />
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Difficulty</label>
                  <select
                    className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                    value={form.difficulty}
                    onChange={(e) => setField("difficulty", e.target.value)}
                  >
                    {["Easy", "Medium", "Hard"].map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {needsAudience && (
              <Field
                label="Target audience"
                value={form.targetAudience}
                onChange={(v) => setField("targetAudience", v)}
              />
            )}

            {needsLanguage && (
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Language</label>
                <select
                  className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                  value={form.language}
                  onChange={(e) => setField("language", e.target.value)}
                >
                  {["Python", "JavaScript", "Java", "C++", "Go", "TypeScript"].map(
                    (x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    )
                  )}
                </select>
              </div>
            )}

            {needsDb && (
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Database type</label>
                <select
                  className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                  value={form.databaseType}
                  onChange={(e) => setField("databaseType", e.target.value)}
                >
                  {["PostgreSQL", "MySQL", "SQLite", "MS SQL Server"].map((x) => (
                    <option key={x} value={x}>
                      {x}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {needsJobMeta && (
              <div className="grid gap-3 md:grid-cols-2">
                <Field
                  label="Job role"
                  value={form.jobRole}
                  onChange={(v) => setField("jobRole", v)}
                />
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">
                    Experience level
                  </label>
                  <select
                    className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
                    value={form.experienceYears}
                    onChange={(e) => setField("experienceYears", e.target.value)}
                  >
                    {[
                      "0-1 (Fresher)",
                      "1-3 (Junior)",
                      "3-5 (Mid-level)",
                      "5-8 (Senior)",
                      "8+ (Staff/Principal)",
                    ].map((x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {needsConcepts && (
              <Field
                label="Concepts (comma separated)"
                value={form.concepts}
                onChange={(v) => setField("concepts", v)}
                placeholder="e.g. classification, NLP, time series"
              />
            )}

            {needsDsaLangs && (
              <div>
                <label className="mb-1 block text-xs text-zinc-500">
                  Starter code languages
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    "python",
                    "java",
                    "javascript",
                    "typescript",
                    "kotlin",
                    "go",
                    "rust",
                    "cpp",
                    "csharp",
                    "c",
                  ].map((lang) => (
                    <label key={lang} className="flex items-center gap-1 text-xs">
                      <input
                        type="checkbox"
                        checked={form.dsaLanguages.includes(lang)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setField("dsaLanguages", [...form.dsaLanguages, lang]);
                          } else {
                            setField(
                              "dsaLanguages",
                              form.dsaLanguages.filter((l) => l !== lang)
                            );
                          }
                        }}
                      />
                      {lang}
                    </label>
                  ))}
                </div>
              </div>
            )}

            {endpoint === "enrich-dsa" && (
              <div>
                <label className="mb-1 block text-xs text-zinc-500">
                  Problem JSON (title, input_output, …)
                </label>
                <textarea
                  className="min-h-[220px] w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs"
                  value={form.enrichDsaJson}
                  onChange={(e) => setField("enrichDsaJson", e.target.value)}
                />
              </div>
            )}
          </section>

          {validationErrors.length > 0 && (
            <div
              className="rounded-lg border border-amber-900/60 bg-amber-950/20 p-3 text-sm text-amber-100"
              role="alert"
            >
              <p className="mb-1 font-medium text-amber-200">Fix before generating</p>
              <ul className="list-inside list-disc text-xs text-amber-100/90">
                {validationErrors.map((err) => (
                  <li key={err}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {(pollHint || loading) && (
            <div
              className="flex flex-col gap-1 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-amber-200/95"
              aria-live="polite"
            >
              {pollHint && <p>{pollHint}</p>}
              {loading && (
                <p className="font-mono text-xs text-zinc-500">
                  Elapsed {Math.floor(elapsedMs / 1000)}s ({elapsedMs} ms)
                </p>
              )}
            </div>
          )}

          <Button
            type="button"
            className="min-h-11 w-full bg-rose-600 text-white hover:bg-rose-500 sm:min-h-10"
            disabled={loading || !effectiveOrgId}
            onClick={() => onSubmit()}
          >
            {loading ? `Working… ${Math.floor(elapsedMs / 1000)}s` : "🚀 Generate"}
          </Button>

          {error && (
            <div className="rounded-md border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">
              {error}
            </div>
          )}
        </div>

        <aside className="h-fit rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-4 text-xs text-zinc-500 shadow-panel">
          <p className="font-semibold text-zinc-400">Request target</p>
          <code className="mt-2 block break-all rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 font-mono text-[11px] text-console-accent/90">
            POST /api/v1/{pathSuffix}
          </code>
          <p className="mt-4 leading-relaxed">
            Point <code className="rounded bg-zinc-900 px-1 text-zinc-400">NEXT_PUBLIC_API_BASE</code>{" "}
            in <code className="text-zinc-400">.env.local</code> at your FastAPI host (default is often{" "}
            <code className="text-zinc-400">http://127.0.0.1:9000</code>).
          </p>
          <p className="mt-3 border-t border-zinc-800/80 pt-3 text-[11px] leading-relaxed text-zinc-600">
            Each successful generation request sends <code className="text-zinc-500">X-Request-Id</code>
            , <code className="text-zinc-500">X-Org-Id</code>, and <code className="text-zinc-500">org_id</code>{" "}
            in the JSON body (resolved from the field or{" "}
            <code className="text-zinc-500">NEXT_PUBLIC_PLAYGROUND_ORG_ID</code>). If the browser blocks
            requests, allow these headers in your API CORS config.
          </p>
        </aside>
      </div>

      {result !== null && (
        <ResponseView data={result} meta={runMeta} orgIdForApi={effectiveOrgId} />
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-zinc-500">{label}</label>
      <input
        className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-400 ring-console-accent/30 focus:outline-none focus:ring-2"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
