"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { adminFetchJson } from "@/lib/adminApi";
import { ArrowLeft, RefreshCw, Search, Eye, Database, BarChart3, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

type SchemaEntry = {
  schema_id: string;
  domain: string;
  total_rows: number;
  min_rows_per_table: number;
  tables_count: number;
  sample_data_row_counts: Record<string, number>;
};

type StatsResponse = {
  total_schemas: number;
  by_domain: { _id: string; count: number }[];
  by_category: { _id: string; count: number }[];
  by_difficulty: { _id: string; count: number }[];
};

type ListResponse = {
  total: number;
  returned: number;
  schemas: SchemaEntry[];
};

export default function SqlSchemasPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [domainFilter, setDomainFilter] = useState("");
  const [viewSchema, setViewSchema] = useState<SchemaEntry | null>(null);
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testCategory, setTestCategory] = useState("join");
  const [testDifficulty, setTestDifficulty] = useState("medium");

  const statsQuery = useQuery({
    queryKey: ["sql-schemas", "stats"],
    queryFn: () => adminFetchJson<StatsResponse>("/api/admin/sql-schemas/stats"),
    refetchInterval: 60_000,
  });

  const listQuery = useQuery({
    queryKey: ["sql-schemas", "list", domainFilter],
    queryFn: () => adminFetchJson<ListResponse>(
      `/api/admin/sql-schemas/list?limit=200${domainFilter ? `&domain=${encodeURIComponent(domainFilter)}` : ""}`
    ),
    refetchInterval: 60_000,
  });

  const schemas = listQuery.data?.schemas ?? [];
  const filtered = schemas.filter(s =>
    !search ||
    s.schema_id.toLowerCase().includes(search.toLowerCase()) ||
    s.domain.toLowerCase().includes(search.toLowerCase())
  );

  const domains = statsQuery.data?.by_domain ?? [];
  const categories = statsQuery.data?.by_category ?? [];

  const handleTestSelect = useCallback(async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const data = await adminFetchJson<Record<string, unknown>>(
        `/api/admin/sql-schemas/select?difficulty=${testDifficulty}&sql_category=${testCategory}&limit=30`
      );
      setTestResult(data);
      toast.success(`Selected: ${data.schema_id}`);
    } catch (err) {
      toast.error(`Failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setTestLoading(false);
    }
  }, [testDifficulty, testCategory]);

  const getRowStatus = (minRows: number) => {
    if (minRows >= 100) return "text-emerald-400";
    if (minRows >= 50) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" className="border-white/10" onClick={() => router.push("/rag")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="text-2xl font-semibold">SQL Schema Management</div>
            <div className="mt-1 text-sm text-zinc-400">
              {statsQuery.data?.total_schemas ?? "—"} schemas · MongoDB RAG service
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            className="border-white/10"
            onClick={() => { statsQuery.refetch(); listQuery.refetch(); }}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Total Schemas</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-zinc-100">
            {statsQuery.data?.total_schemas?.toLocaleString() ?? "—"}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Unique Domains</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-zinc-100">
            {domains.length || "—"}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">100 rows/table</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-emerald-400">
            {schemas.filter(s => s.min_rows_per_table >= 100).length || "—"}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="text-xs text-zinc-500">Low rows (&lt;50)</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-red-400">
            {schemas.filter(s => s.min_rows_per_table < 50).length}
          </div>
        </div>
      </div>

      {/* Category coverage */}
      {categories.length > 0 && (
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-300">
            <BarChart3 className="h-4 w-4 text-cyan-400" /> Category Coverage
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map(c => (
              <span key={c._id} className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300">
                {c._id} <span className="text-cyan-500">{c.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Test schema selection */}
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-300">
          <Filter className="h-4 w-4 text-purple-400" /> Test Schema Selection
        </div>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <div className="mb-1 text-xs text-zinc-500">Category</div>
            <select
              className="h-9 rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={testCategory}
              onChange={e => setTestCategory(e.target.value)}
            >
              {["select","join","aggregation","subquery","window","cte"].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="mb-1 text-xs text-zinc-500">Difficulty</div>
            <select
              className="h-9 rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
              value={testDifficulty}
              onChange={e => setTestDifficulty(e.target.value)}
            >
              {["easy","medium","hard"].map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <Button
            variant="outline"
            className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            onClick={handleTestSelect}
            disabled={testLoading}
          >
            <Database className={`mr-1.5 h-3.5 w-3.5 ${testLoading ? "animate-spin" : ""}`} />
            {testLoading ? "Selecting…" : "Test Select"}
          </Button>
        </div>
        {testResult && (
          <div className="rounded-lg border border-white/5 bg-zinc-950 p-3 text-xs text-zinc-300">
            <div className="mb-1 font-medium text-cyan-300">{String(testResult.schema_id)}</div>
            <div className="text-zinc-500">
              domain: {String(testResult.domain)} · 
              tables: {String((testResult.metadata as Record<string,unknown>)?.table_count ?? "?")} · 
              columns: {String((testResult.metadata as Record<string,unknown>)?.total_columns ?? "?")}
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            className="h-10 w-full rounded-lg border border-white/10 bg-zinc-900 pl-9 pr-4 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
            placeholder="Search by schema_id or domain..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="h-10 rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-zinc-200"
          value={domainFilter}
          onChange={e => setDomainFilter(e.target.value)}
        >
          <option value="">All domains</option>
          {domains.map(d => (
            <option key={d._id} value={d._id}>{d._id} ({d.count})</option>
          ))}
        </select>
      </div>

      {/* Schema table */}
      <div className="rounded-xl border border-white/10 bg-zinc-950/40 overflow-hidden">
        {listQuery.isLoading ? (
          <div className="px-4 py-8 text-center text-sm text-zinc-500">Loading schemas…</div>
        ) : filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-zinc-500">No schemas found.</div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3">Schema ID</th>
                  <th className="px-4 py-3">Domain</th>
                  <th className="px-4 py-3">Tables</th>
                  <th className="px-4 py-3">Min rows/table</th>
                  <th className="px-4 py-3">Total rows</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {filtered.map((schema, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2 font-mono text-xs text-cyan-200">{schema.schema_id}</td>
                    <td className="px-4 py-2 text-xs text-zinc-400">{schema.domain}</td>
                    <td className="px-4 py-2 text-xs text-zinc-400">{schema.tables_count}</td>
                    <td className={`px-4 py-2 text-xs font-semibold ${getRowStatus(schema.min_rows_per_table)}`}>
                      {schema.min_rows_per_table}
                    </td>
                    <td className="px-4 py-2 text-xs text-zinc-400">{schema.total_rows?.toLocaleString()}</td>
                    <td className="px-4 py-2">
                      <Button
                        variant="outline"
                        className="border-white/10 text-xs h-7 px-2"
                        onClick={() => setViewSchema(schema)}
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Schema detail modal */}
      {viewSchema && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setViewSchema(null)}>
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-xl border border-white/10 bg-zinc-900 p-6" onClick={e => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="font-semibold text-zinc-100">{viewSchema.schema_id}</div>
                <div className="text-xs text-zinc-500 mt-1">domain: {viewSchema.domain}</div>
              </div>
              <Button variant="outline" className="border-white/10 text-xs" onClick={() => setViewSchema(null)}>Close</Button>
            </div>
            <div className="mb-3 text-xs font-medium text-zinc-400">Row counts per table:</div>
            <div className="space-y-1">
              {Object.entries(viewSchema.sample_data_row_counts ?? {}).map(([table, count]) => (
                <div key={table} className="flex items-center justify-between rounded-lg bg-zinc-950 px-3 py-1.5 text-xs">
                  <span className="font-mono text-cyan-300">{table}</span>
                  <span className={`font-semibold ${getRowStatus(count as number)}`}>{count as number} rows</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
