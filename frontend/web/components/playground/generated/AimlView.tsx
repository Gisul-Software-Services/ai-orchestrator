"use client";

import { useMemo, useState } from "react";
import {
  BarChart3,
  ClipboardList,
  FlaskConical,
  ListTodo,
  Pencil,
  RefreshCw,
  Settings2,
  Tags,
} from "lucide-react";
import { fetchAimlCatalogPreview } from "@/lib/aimlCatalogPreview";
import { Collapsible } from "./Collapsible";
import { CodeBlock } from "./CodeBlock";
import { isRecord } from "./types";

const STRATEGY_LABEL: Record<string, string> = {
  library: "Library dataset",
  synthetic: "Synthetic dataset",
  synthetic_fallback: "Synthetic fallback",
};

export function AimlView({
  p,
  index,
  orgIdForApi = "",
}: {
  p: Record<string, unknown>;
  index: number;
  orgIdForApi?: string;
}) {
  const datasetBase = isRecord(p.dataset) ? p.dataset : null;
  const [previewOverride, setPreviewOverride] = useState<unknown[] | null>(null);
  const dataset = useMemo(() => {
    if (!datasetBase) return null;
    if (previewOverride && previewOverride.length > 0) {
      return {
        ...datasetBase,
        data: previewOverride,
        data_preview: true,
      };
    }
    return datasetBase;
  }, [datasetBase, previewOverride]);

  const tasks = Array.isArray(p.tasks) ? p.tasks : [];
  const criteria = Array.isArray(p.evaluationCriteria) ? p.evaluationCriteria : [];
  const pre = Array.isArray(p.preprocessing_requirements)
    ? p.preprocessing_requirements
    : [];
  const strategy = String(p.dataset_strategy ?? "");
  const diff = String(p.difficulty ?? "—");
  const catalogId =
    datasetBase && String(datasetBase.catalog_id ?? "").trim()
      ? String(datasetBase.catalog_id).trim()
      : "";
  const isLib =
    strategy === "library" || String(datasetBase?.storage_type ?? "") === "library";

  return (
    <article className="overflow-hidden rounded-xl border border-zinc-800/90 bg-zinc-950/40 shadow-panel">
      <div className="border-b border-zinc-800/80 px-4 py-3 sm:px-5 sm:py-4">
        <h4 className="text-base font-semibold tracking-tight text-zinc-50">
          AI/ML problem {index}
        </h4>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">
          {String(p.problemStatement ?? "")}
        </p>
        {strategy && (
          <p className="mt-3 text-xs text-zinc-500">
            Dataset strategy:{" "}
            <span className="font-medium text-zinc-400">
              {STRATEGY_LABEL[strategy] ?? strategy}
            </span>
          </p>
        )}
      </div>

      <div className="space-y-2 p-3 sm:space-y-2.5 sm:p-4">
        {isLib && catalogId ? (
          <CatalogPreviewFetchBar
            catalogId={catalogId}
            orgId={orgIdForApi}
            onRows={(rows) => setPreviewOverride(rows)}
          />
        ) : null}
        {dataset && (
          <DatasetPreviewLead dataset={dataset} strategy={strategy} />
        )}

        {tasks.length > 0 && (
          <Collapsible title="Tasks" icon={<ListTodo strokeWidth={1.75} />} defaultOpen>
            <ul className="list-inside list-disc space-y-1 text-sm leading-relaxed text-zinc-300">
              {tasks.map((t, i) => (
                <li key={i}>{String(t)}</li>
              ))}
            </ul>
          </Collapsible>
        )}

        {dataset && <DatasetDisplay dataset={dataset} />}

        {p.starter_code != null && String(p.starter_code).length > 0 ? (
          <Collapsible title="Starter code" icon={<Pencil strokeWidth={1.75} />}>
            <StarterCodeBlock sc={p.starter_code} />
          </Collapsible>
        ) : null}

        {pre.length > 0 && (
          <Collapsible
            title="Preprocessing requirements"
            icon={<Settings2 strokeWidth={1.75} />}
          >
            <ul className="list-inside list-disc space-y-1 text-sm leading-relaxed text-zinc-300">
              {pre.map((r, i) => (
                <li key={i}>{String(r)}</li>
              ))}
            </ul>
          </Collapsible>
        )}

        {p.expectedApproach != null && String(p.expectedApproach).length > 0 ? (
          <Collapsible title="Expected approach" icon={<FlaskConical strokeWidth={1.75} />}>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">
              {String(p.expectedApproach)}
            </p>
          </Collapsible>
        ) : null}

        {criteria.length > 0 && (
          <Collapsible title="Evaluation criteria" icon={<Tags strokeWidth={1.75} />}>
            <ul className="list-inside list-disc space-y-1 text-sm leading-relaxed text-zinc-300">
              {criteria.map((c, i) => (
                <li key={i}>{String(c)}</li>
              ))}
            </ul>
          </Collapsible>
        )}
      </div>

      <footer className="flex flex-wrap items-center gap-2 border-t border-zinc-800/80 px-4 py-3 sm:px-5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          Difficulty
        </span>
        <span className="rounded-md border border-zinc-700/80 bg-zinc-900/80 px-2.5 py-0.5 text-xs font-medium text-zinc-100">
          {diff}
        </span>
      </footer>
    </article>
  );
}

function CatalogPreviewFetchBar({
  catalogId,
  orgId,
  onRows,
}: {
  catalogId: string;
  orgId: string;
  onRows: (rows: Record<string, unknown>[]) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const run = async () => {
    setMsg(null);
    setLoading(true);
    try {
      const r = await fetchAimlCatalogPreview(catalogId, {
        orgId: orgId.trim() || undefined,
      });
      if (r.preview_available && r.rows.length > 0) {
        onRows(r.rows);
        return;
      }
      if (r.reason === "openml_only") {
        setMsg(
          "Server preview only supports catalog entries that load via fetch_openml. For sklearn, seaborn, Hugging Face, or Keras loaders, run the Python load code locally (browser cannot execute it)."
        );
        return;
      }
      if (r.reason === "preview_disabled") {
        setMsg("Preview is disabled on the API (AIML_LIBRARY_DATA_PREVIEW).");
        return;
      }
      setMsg(
        "No preview returned (dataset too large, fetch failed, or offline). Use load code locally."
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Preview request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-zinc-700/70 bg-zinc-900/50 px-3 py-2.5 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-zinc-500">Tabular preview</span>
        <button
          type="button"
          disabled={loading}
          onClick={() => void run()}
          className="inline-flex items-center gap-1.5 rounded-md border border-zinc-600 bg-zinc-950 px-2.5 py-1 text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
            strokeWidth={2}
          />
          {loading ? "Loading…" : "Load / refresh from API"}
        </button>
        {!orgId.trim() ? (
          <span className="text-amber-200/85" title="Required when API org gate is on">
            Add Org ID in the playground (X-Org-Id) if requests return 401/403.
          </span>
        ) : null}
      </div>
      {msg ? (
        <p className="mt-2 leading-relaxed text-amber-200/90">{msg}</p>
      ) : null}
    </div>
  );
}

/** Prominent dataset block: sample rows (synthetic) or library overview (no API rows). */
function DatasetPreviewLead({
  dataset,
  strategy,
}: {
  dataset: Record<string, unknown>;
  strategy: string;
}) {
  const data = dataset.data;
  const hasRows = Array.isArray(data) && data.length > 0;
  const isLibrary =
    strategy === "library" || String(dataset.storage_type ?? "") === "library";
  const isCatalogPreview = Boolean(dataset.data_preview);

  if (hasRows) {
    return (
      <section className="rounded-xl border border-cyan-900/45 bg-gradient-to-b from-cyan-950/25 to-zinc-950/40 p-4 shadow-[inset_0_1px_0_0_rgba(34,211,238,0.06)]">
        <h5 className="mb-3 flex items-center gap-2 text-sm font-semibold tracking-tight text-zinc-100">
          <BarChart3 className="h-4 w-4 shrink-0 text-console-accent" strokeWidth={1.75} />
          {isCatalogPreview ? "Dataset preview (catalog)" : "Generated dataset (sample rows)"}
        </h5>
        <p className="mb-3 text-xs leading-relaxed text-zinc-500">
          {isCatalogPreview
            ? "First rows loaded on the API server from OpenML/sklearn for quick inspection. Use the load code below for the full dataset locally."
            : "Model-generated tabular preview. Full volume may be larger than shown."}
        </p>
        <DatasetRowsPreview data={data} maxRows={isCatalogPreview ? 25 : 50} />
      </section>
    );
  }

  if (isLibrary) {
    return <LibraryDatasetOverview dataset={dataset} />;
  }

  return null;
}

function LibraryDatasetOverview({ dataset }: { dataset: Record<string, unknown> }) {
  const tags = Array.isArray(dataset.tags) ? dataset.tags : [];
  const pip = dataset.pip_install != null ? String(dataset.pip_install) : "";
  const fi = dataset.features_info != null ? String(dataset.features_info) : "";
  const useCase = dataset.use_case != null ? String(dataset.use_case) : "";
  const cat = dataset.category != null ? String(dataset.category) : "";
  const hasImport = Boolean(dataset.import_code);
  const hasLoad = Boolean(dataset.load_code);

  return (
    <section className="rounded-xl border border-violet-900/40 bg-violet-950/15 p-4">
      <h5 className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-100">
        <BarChart3 className="h-4 w-4 shrink-0 text-violet-400" strokeWidth={1.75} />
        Library dataset
      </h5>
      <p className="text-xs leading-relaxed text-zinc-500">
        Rows are loaded in your environment via the code below — the API does not ship raw rows for
        catalog datasets.
      </p>
      {dataset.name != null && String(dataset.name).length > 0 && (
        <p className="mt-3 text-sm font-medium text-zinc-200">{String(dataset.name)}</p>
      )}
      {cat && (
        <p className="mt-1 text-[11px] uppercase tracking-wide text-zinc-500">
          Category · <span className="text-zinc-400">{cat}</span>
        </p>
      )}
      {tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tags.map((t, i) => (
            <span
              key={i}
              className="rounded-md border border-zinc-700/80 bg-zinc-900/60 px-2 py-0.5 text-[11px] text-zinc-300"
            >
              {String(t)}
            </span>
          ))}
        </div>
      )}
      {fi && (
        <div className="mt-4 space-y-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Columns &amp; features
          </p>
          <p className="text-sm leading-relaxed text-zinc-300">{fi}</p>
        </div>
      )}
      {useCase && (
        <div className="mt-3 space-y-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Use case</p>
          <p className="text-sm leading-relaxed text-zinc-400">{useCase}</p>
        </div>
      )}
      {pip && (
        <div className="mt-4 space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Install (local)
          </p>
          <CodeBlock code={pip} language="bash" />
        </div>
      )}

      {(hasImport || hasLoad) && (
        <section className="mt-4 space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Import &amp; load (run locally)
          </p>
          <CodeBlock
            code={
              hasImport && hasLoad
                ? `${String(dataset.import_code)}\n\n${String(dataset.load_code)}`
                : hasLoad
                  ? String(dataset.load_code)
                  : String(dataset.import_code)
            }
            language="python"
          />
          <p className="rounded-lg border border-amber-900/35 bg-amber-950/25 px-3 py-2 text-xs leading-relaxed text-amber-100/90">
            Run in a Python notebook or REPL; this console does not execute code.
          </p>
        </section>
      )}
    </section>
  );
}

function DatasetDisplay({ dataset }: { dataset: Record<string, unknown> }) {
  const hasImport = Boolean(dataset.import_code);
  const hasLoad = Boolean(dataset.load_code);
  const features = Array.isArray(dataset.features) ? dataset.features : [];
  const featureTypes = dataset.feature_types;
  const title =
    dataset.name != null && String(dataset.name).trim() !== ""
      ? String(dataset.name)
      : "Dataset details";

  return (
    <Collapsible
      title={title}
      icon={<BarChart3 strokeWidth={1.75} />}
      defaultOpen={false}
      contentClassName="space-y-4"
    >
      {dataset.catalog_id != null && String(dataset.catalog_id).length > 0 && (
        <p className="font-mono text-[11px] text-zinc-500">ID: {String(dataset.catalog_id)}</p>
      )}

      {dataset.description != null && String(dataset.description).trim() !== "" && (
        <p className="text-sm leading-relaxed text-zinc-300">
          {String(dataset.description)}
        </p>
      )}

      <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
        <div className="flex gap-1.5">
          <dt className="font-medium text-zinc-500">Domain</dt>
          <dd className="text-zinc-400">{String(dataset.domain ?? "—")}</dd>
        </div>
        <span className="hidden text-zinc-700 sm:inline" aria-hidden>
          |
        </span>
        <div className="flex gap-1.5">
          <dt className="font-medium text-zinc-500">Source</dt>
          <dd className="text-zinc-400">{String(dataset.source ?? "—")}</dd>
        </div>
        <span className="hidden text-zinc-700 sm:inline" aria-hidden>
          |
        </span>
        <div className="flex gap-1.5">
          <dt className="font-medium text-zinc-500">Target</dt>
          <dd className="text-zinc-400">{String(dataset.target ?? "—")}</dd>
        </div>
        <span className="hidden text-zinc-700 sm:inline" aria-hidden>
          |
        </span>
        <div className="flex gap-1.5">
          <dt className="font-medium text-zinc-500">Size</dt>
          <dd className="text-zinc-400">{String(dataset.size ?? "—")}</dd>
        </div>
      </dl>

      {hasImport && !hasLoad && (
        <section className="space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Import code
          </p>
          <CodeBlock code={String(dataset.import_code)} language="python" />
        </section>
      )}

      {hasLoad && (
        <section className="space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Load code (run in notebook)
          </p>
          <CodeBlock
            code={
              hasImport
                ? `${String(dataset.import_code)}\n\n${String(dataset.load_code)}`
                : String(dataset.load_code)
            }
            language="python"
          />
          <p className="rounded-lg border border-amber-900/35 bg-amber-950/25 px-3 py-2 text-xs leading-relaxed text-amber-100/90">
            Run the snippets locally in a Python notebook or REPL; this console does not
            execute code.
          </p>
        </section>
      )}

      {features.length > 0 && (
        <section className="space-y-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Features ({features.length})
          </p>
          <p className="text-sm leading-relaxed text-zinc-400">
            {features.map(String).join(", ")}
          </p>
        </section>
      )}

      {featureTypes != null && (
        <Collapsible
          title="Feature types"
          icon={<ClipboardList strokeWidth={1.75} />}
          className="border-zinc-800/60 bg-zinc-950/20"
        >
          <pre className="max-h-48 overflow-auto rounded-lg border border-zinc-800/80 bg-zinc-950 p-3 font-mono text-xs leading-relaxed text-zinc-400">
            {typeof featureTypes === "string"
              ? featureTypes
              : JSON.stringify(featureTypes, null, 2)}
          </pre>
        </Collapsible>
      )}
    </Collapsible>
  );
}

function StarterCodeBlock({ sc }: { sc: unknown }) {
  if (isRecord(sc)) {
    const py = sc.python3 ?? sc.python;
    if (py) return <CodeBlock code={String(py)} language="python" />;
  }
  return <CodeBlock code={String(sc)} language="python" />;
}

function DatasetRowsPreview({
  data,
  maxRows = 25,
}: {
  data: unknown;
  maxRows?: number;
}) {
  if (!Array.isArray(data) || data.length === 0) return null;
  const sample = data.slice(0, maxRows);
  const first = sample[0];
  if (!isRecord(first)) {
    return (
      <section className="space-y-1.5">
        <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
          Sample data (raw)
        </p>
        <pre className="max-h-48 overflow-auto rounded-lg border border-zinc-800/80 bg-zinc-950 p-3 text-xs leading-relaxed text-zinc-400">
          {JSON.stringify(sample, null, 2)}
        </pre>
      </section>
    );
  }
  const keys = Object.keys(first);
  return (
    <section className="space-y-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
        Sample rows{" "}
        <span className="font-normal text-zinc-600">
          ({sample.length} of {data.length})
        </span>
      </p>
      <div className="overflow-hidden rounded-lg border border-zinc-800/80">
        <div className="max-h-[min(28rem,70vh)] overflow-x-auto overflow-y-auto">
          <table className="w-full min-w-max border-collapse text-left text-xs">
            <thead className="sticky top-0 z-10 bg-zinc-900/95 shadow-sm backdrop-blur-sm">
              <tr className="border-b border-zinc-800 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                {keys.map((k) => (
                  <th key={k} className="whitespace-nowrap px-3 py-2 font-semibold">
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/70">
              {sample.map((row, ri) => {
                if (!isRecord(row)) return null;
                return (
                  <tr
                    key={ri}
                    className="bg-zinc-950/40 transition-colors hover:bg-zinc-900/50"
                  >
                    {keys.map((k) => (
                      <td
                        key={k}
                        className="max-w-[14rem] whitespace-nowrap px-3 py-2 font-mono text-zinc-300 first:pl-3 last:pr-3"
                        title={formatCell(row[k])}
                      >
                        <span className="block max-w-[14rem] truncate">
                          {formatCell(row[k])}
                        </span>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
