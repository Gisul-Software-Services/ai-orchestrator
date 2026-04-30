# Design Document: Admin Console Redesign

## Overview

The Gisul Admin Console is a Next.js 14 (App Router) + Tailwind CSS + Recharts internal dashboard for an AI platform. The current implementation has several data-wiring bugs, a duplicate sidebar component, a missing `darkMode` config, and inconsistent UI polish across its eight pages.

This redesign is a targeted, production-ready fix that:
- Corrects all data-wiring bugs (wrong latency units, null/empty states, missing formatting)
- Consolidates the sidebar to a single component
- Brings every page to a consistent, polished standard
- Removes `(data as any)` casts in favour of typed interfaces
- Preserves the existing dark theme with cyan accent (`#22d3ee`)

The approach is surgical: we modify only the files that need changing, reuse all existing hooks and API routes, and do not introduce new dependencies.

---

## Architecture

The application follows Next.js 14 App Router conventions with a client-side data layer built on TanStack Query (React Query).

```
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  app/layout.tsx                                      │   │
│  │  ┌──────────┐  ┌──────────────────────────────────┐  │   │
│  │  │ Sidebar  │  │  main                            │  │   │
│  │  │ .tsx     │  │  ┌──────────────────────────┐    │  │   │
│  │  │          │  │  │ TopBar.tsx               │    │  │   │
│  │  │ nav      │  │  └──────────────────────────┘    │  │   │
│  │  │ items    │  │  ┌──────────────────────────┐    │  │   │
│  │  │ health   │  │  │ page.tsx (per route)     │    │  │   │
│  │  │ footer   │  │  │  └─ panel components     │    │  │   │
│  │  └──────────┘  │  └──────────────────────────┘    │  │   │
│  │                └──────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Data Layer (TanStack Query)                                │
│  useHealthQuery · useStatsQuery · useMetricsInferenceQuery  │
│  useMetricsGpuQuery · useMetricsQueuesQuery                 │
│  useSettingsQuery (parallel: health + stats + inference)    │
└─────────────────────────────────────────────────────────────┘
         │ fetch /api/admin/*
┌─────────────────────────────────────────────────────────────┐
│  Next.js API Routes (server-side proxy)                     │
│  /api/admin/health · /api/admin/stats                       │
│  /api/admin/metrics/{gpu,inference,queues,overview}         │
└─────────────────────────────────────────────────────────────┘
         │ HTTP + X-Api-Key header
┌─────────────────────────────────────────────────────────────┐
│  Python Model Service (port 7000)                           │
└─────────────────────────────────────────────────────────────┘
```

**Key architectural decisions:**
- All API calls go through Next.js server-side proxy routes (`/api/admin/*`) so the `ADMIN_API_KEY` never reaches the browser.
- TanStack Query handles caching, background refetch, and stale-while-revalidate for all data.
- `useSettingsQuery` is refactored to fan out three parallel queries (health + stats + inference) and merge results client-side, eliminating the dependency on a non-existent `/api/admin/settings` endpoint.

---

## Components and Interfaces

### Layout Components

#### `components/layout/Sidebar.tsx` (updated)
Single consolidated sidebar. `AppSidebar.tsx` is deleted.

```
Props: none (reads pathname from usePathname, health from useHealthQuery)

Nav items (8):
  /dashboard     → Dashboard      (LayoutDashboard icon)
  /playground    → Playground     (Play icon)
  /monitoring    → Monitoring     (Activity icon)
  /usage         → Usage & Billing (BarChart3 icon)
  /orgs          → Orgs & Keys    (Users icon)
  /rag           → RAG Management (Database icon)
  /history       → History        (History icon)
  /settings      → Settings       (Settings icon)

Active detection: pathname === href || pathname.startsWith(href + "/")
Active style: bg-zinc-800/90 text-white ring-1 ring-zinc-700/60
Active icon: text-console-accent
Active dot: h-1.5 w-1.5 bg-console-accent shadow-[0_0_8px_rgba(34,211,238,0.8)]

Footer: ModelStatusDot using useHealthQuery
  - model_loaded=true  → bg-emerald-400 "Model loaded"
  - model_loaded=false → bg-red-400 "Model not loaded"
  - isError            → bg-zinc-500 "Unreachable"
```

#### `components/layout/TopBar.tsx` (updated)
Remove the subtitle paragraph. Keep: page title + user badge + ThemeToggle.

```
Before: <p>Internal admin console — authenticated staff only</p>
After:  (removed)
```

### Dashboard Panel Components

#### `components/dashboard/InferencePanel.tsx` (updated)
Fix latency unit: accept `avgLatencyMs` (number | null) instead of `avgLatencySeconds`.

```
Prop change:
  avgLatencySeconds: number | null  →  avgLatencyMs: number | null

Display:
  fmtMs(n) = typeof n === "number" ? `${n.toFixed(0)} ms` : "—"
  Label: "Avg latency" (unchanged)
```

#### `components/dashboard/GpuPanel.tsx` (updated)
When `gpu.available === false`, show "GPU unavailable" card with error reason as subtitle.

```
Logic:
  if (!gpu?.available) {
    value = "GPU unavailable"
    subtitle = gpu?.error ?? "NVML not available"
    indicatorColor = "zinc"
  }
```

#### `components/dashboard/CachePanel.tsx` (updated)
When hits + misses are both 0/null, show "No cache data yet" empty state instead of 0%/100% donut.

```
isEmpty = (hits === 0 || hits === null) && (misses === 0 || misses === null)
if (isEmpty) → render empty state message, no PieChart
```

#### `components/dashboard/QueuePanel.tsx` (updated)
When `queue_depths` is `{}`, show "All queues empty" with green dot.

```
isEmpty = Object.keys(queues?.queue_depths ?? {}).length === 0
if (isEmpty && !loading && !error) → render green-dot empty state
```

### Page Components

#### `app/dashboard/page.tsx` (updated)
Remove `(data as any)` casts. Use typed `InferenceMetrics` from `types/api.ts`. Compute latency in ms.

```
Before:
  const totalGenSeconds = (inferenceQ.data as any)?.total_generation_time_seconds
  avgLatencySeconds = totalGenSeconds / totalRequests

After:
  const inferenceData: InferenceMetrics | undefined = inferenceQ.data
  const totalGenSeconds = inferenceData?.total_generation_time_seconds
  avgLatencyMs = (totalGenSeconds / totalRequests) * 1000
  // Pass avgLatencyMs to InferencePanel
```

#### `app/settings/page.tsx` (redesigned)
Derive all data from `useSettingsQuery` which now returns `{ health, stats, inference }`.

Sections:
1. **Model Status** — `health.model_loaded`, `health.memory_gb`, `health.active_jobs`, `health.total_jobs_in_store`
2. **Runtime Stats** — `stats.total_requests`, `stats.cache_hit_rate_percent`, `stats.avg_batch_size`, `stats.batches_processed`, `stats.errors`
3. **Uptime** — derived from `inference.server_start_time` (ISO → human-readable duration)
4. **Server Configuration** — existing fields, replacing `"—"` with `"Not configured"`

#### `app/monitoring/page.tsx` (updated)
Fix null stats cards:
- `totalRequestsAllTime === null` → value="No data", subtitle="Stats endpoint unavailable"
- `avgBatchSize === null` → same
- `cacheHitRateStats === null` → empty state in cache card (no donut)
- `errorRate === null` → value="No requests"

#### `app/history/page.tsx` (updated)
Fix number formatting in stats cards:
- `stats.total` → `stats.total.toLocaleString()`
- `stats.avgLatency` → `` `${stats.avgLatency} ms` ``
- `stats.errorRate` → `` `${stats.errorRate.toFixed(2)}%` ``

#### `app/playground/page.tsx` (updated)
Fix empty states in request count badge:
- `statsQ.isLoading` → `<Skeleton className="h-3 w-10" />`
- `statsQ.isError` → `"—"` with `text-zinc-500`
- count === 0 && isSuccess → `"0 req"` (not blank)

### Hooks

#### `hooks/useSettings.ts` (refactored)
Replace single `/api/admin/settings` fetch with three parallel queries.

```typescript
export function useSettingsQuery() {
  const healthQ = useHealthQuery();
  const statsQ = useStatsQuery();
  const inferenceQ = useMetricsInferenceQuery();

  return {
    isLoading: healthQ.isLoading || statsQ.isLoading || inferenceQ.isLoading,
    isError: healthQ.isError && statsQ.isError && inferenceQ.isError,
    data: {
      source: "derived" as const,
      data: {
        health: healthQ.data ?? null,
        stats: statsQ.data ?? null,
        inference: inferenceQ.data ?? null,
      },
    },
  };
}
```

### Config

#### `tailwind.config.ts`
Already has `darkMode: "class"` — no change needed (confirmed from source).

---

## Data Models

All types live in `frontend/web/types/api.ts`. The existing types are correct and complete. No new types are needed; the fix is to use them instead of `(data as any)`.

```typescript
// Already defined — use these everywhere:

interface InferenceMetrics {
  total_requests: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate_percent: number;
  requests_by_endpoint: Record<string, number>;
  errors: number;
  batches_processed: number;
  avg_batch_size: number;
  total_generation_time_seconds: number;
  server_start_time: string | null;
}

interface GpuMetrics {
  available: boolean;
  error?: string | null;
  gpu_util_percent?: number;
  memory_used_percent?: number;
  memory_used_mb?: number;
  memory_total_mb?: number;
  temperature_c?: number;
  power_watts?: number | null;
}

interface HealthResponse {
  status: string;
  model_loaded: boolean;
  memory_gb: number;
  queue_sizes: Record<string, number>;
  active_jobs: number;
  total_jobs_in_store: number;
}

interface StatsResponse {
  total_requests: number;
  cache_hit_rate_percent: number;
  requests_by_endpoint: Record<string, number>;
  batches_processed: number;
  avg_batch_size: number;
  errors: number;
}
```

### Latency Computation

The latency formula is the central data-wiring fix:

```
avgLatencyMs = (total_generation_time_seconds / total_requests) * 1000
```

This must be computed in `dashboard/page.tsx` (before passing to `InferencePanel`) and the prop renamed from `avgLatencySeconds` to `avgLatencyMs`.

### Cache Empty State Logic

```
isEmpty(hits, misses) =
  (hits === null || hits === 0) && (misses === null || misses === 0)
```

When `isEmpty` is true, render the empty state. When false, render the donut with:
```
pieData = [
  { name: "Hit",  value: Math.max(0, cacheHitRatePercent) },
  { name: "Miss", value: Math.max(0, 100 - cacheHitRatePercent) },
]
// Invariant: pieData[0].value + pieData[1].value === 100
```

### Uptime Computation

```
uptime_seconds = Math.max(0, Math.floor((Date.now() - Date.parse(server_start_time)) / 1000))
```

Displayed as a human-readable string (e.g. "2 hours 14 minutes") using `date-fns/formatDistanceStrict`.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

**PBT applicability assessment:** This feature involves pure data transformation functions (latency formula, cache hit rate split, number formatting, uptime computation, sidebar active-state logic). These are pure functions with clear input/output behavior and universal properties that hold across a wide input space. PBT is appropriate for these functions. UI rendering, infrastructure wiring, and TypeScript type checks are excluded from PBT.

**Property reflection:** After reviewing all testable criteria, the following consolidations apply:
- Properties 3 and 4 (GpuPanel unavailable state + error string) can be combined into one comprehensive GPU unavailable property.
- Properties 6 and 7 (Settings HealthResponse fields + StatsResponse fields) are distinct sections and remain separate.
- Properties 9 and 10 (History formatting) cover different fields and remain separate.
- No further redundancy identified.

---

### Property 1: Latency unit correctness

*For any* `totalGenSeconds > 0` and `totalRequests > 0`, the computed average latency in milliseconds must equal `(totalGenSeconds / totalRequests) * 1000`, must be strictly positive, and the displayed string must end with `"ms"`.

**Validates: Requirements 3.1**

---

### Property 2: Cache donut invariant

*For any* `cacheHitRatePercent` in the range `[0, 100]`, the donut chart data array must have exactly two entries where the first entry equals `cacheHitRatePercent`, the second equals `100 - cacheHitRatePercent`, and their sum equals exactly `100`.

**Validates: Requirements 5.2**

---

### Property 3: Cache empty state

*For any* combination of `hits` and `misses` where both are `null` or `0`, the CachePanel must render an empty-state message and must NOT render a PieChart element.

**Validates: Requirements 5.1**

---

### Property 4: GPU unavailable state

*For any* `GpuMetrics` where `available === false`, all GPU stat cards must display the unavailable label (not a numeric value), and if `error` is a non-empty string, that string must appear as a subtitle in the rendered output.

**Validates: Requirements 4.1, 4.2**

---

### Property 5: Sidebar active state uniqueness

*For any* pathname from the set of defined nav hrefs, exactly one nav item must be marked active (have the active CSS class and glowing dot), and it must be the item whose `href` is the most specific prefix match for the pathname.

**Validates: Requirements 2.5**

---

### Property 6: Settings uptime non-negative

*For any* `server_start_time` ISO string representing a moment in the past, the computed uptime in seconds must be non-negative (`>= 0`).

**Validates: Requirements 6.2**

---

### Property 7: History total formatting

*For any* non-negative integer `total`, the displayed value in the History page stats card must equal `total.toLocaleString()`.

**Validates: Requirements 11.1**

---

### Property 8: History latency formatting

*For any* non-negative number `avgLatency`, the displayed value must be the string `` `${avgLatency} ms` ``.

**Validates: Requirements 11.2**

---

### Property 9: History error rate formatting

*For any* `errorRate` in `[0, 100]`, the displayed value must be the string `` `${errorRate.toFixed(2)}%` ``.

**Validates: Requirements 11.3**

---

### Property 10: Queue sort order

*For any* `queue_depths` map with at least one entry, the rendered queue rows must appear in descending order of depth (highest depth first).

**Validates: Requirements 8.3**

---

## Error Handling

### Model Service Unreachable
Every page that fetches from `/api/admin/*` must handle `isError` from TanStack Query:
- Show a non-blocking amber banner: `border-amber-500/30 bg-amber-500/10 text-amber-200`
- Continue rendering last known data where available (TanStack Query's stale data)
- Do not throw or crash the page

### Null / Missing Data Fields
Each panel has a defined empty state:

| Panel | Condition | Empty State |
|-------|-----------|-------------|
| InferencePanel | `totalRequests === 0` or fields null | `"—"` for latency |
| GpuPanel | `gpu.available === false` | `"GPU unavailable"` + error subtitle |
| CachePanel | hits=0/null AND misses=0/null | `"No cache data yet"` |
| QueuePanel | `queue_depths === {}` | `"All queues empty"` + green dot |
| Monitoring stats | `totalRequestsAllTime === null` | `"No data"` + `"Stats endpoint unavailable"` |
| Monitoring error rate | `errorRate === null` | `"No requests"` |
| Settings fields | field not in any endpoint | `"Not configured"` (not `"—"`) |

### TypeScript Type Safety
- Remove all `(data as any)` casts in core data paths
- Use typed interfaces from `types/api.ts`
- For genuinely unknown fields, use `unknown` + type guard functions

---

## Testing Strategy

### Dual Testing Approach

Unit tests cover specific examples, edge cases, and error conditions. Property-based tests verify universal properties across all inputs. Both are complementary.

### Property-Based Testing

**Library:** [fast-check](https://github.com/dubzzz/fast-check) (TypeScript-native, works with Vitest/Jest)

**Configuration:** Minimum 100 iterations per property test.

**Tag format:** `// Feature: admin-console-redesign, Property N: <property_text>`

Each correctness property maps to a single property-based test:

| Property | Test file | Arbitraries |
|----------|-----------|-------------|
| 1 — Latency unit | `__tests__/latency.test.ts` | `fc.float({ min: 0.001 })` × 2 |
| 2 — Cache donut invariant | `__tests__/cachePanel.test.ts` | `fc.float({ min: 0, max: 100 })` |
| 3 — Cache empty state | `__tests__/cachePanel.test.ts` | `fc.constantFrom(null, 0)` × 2 |
| 4 — GPU unavailable | `__tests__/gpuPanel.test.ts` | `fc.string()` for error |
| 5 — Sidebar active state | `__tests__/sidebar.test.ts` | `fc.constantFrom(...NAV_HREFS)` |
| 6 — Settings uptime | `__tests__/settings.test.ts` | `fc.date({ max: new Date() })` |
| 7 — History total | `__tests__/history.test.ts` | `fc.integer({ min: 0 })` |
| 8 — History latency | `__tests__/history.test.ts` | `fc.float({ min: 0 })` |
| 9 — History error rate | `__tests__/history.test.ts` | `fc.float({ min: 0, max: 100 })` |
| 10 — Queue sort | `__tests__/queuePanel.test.ts` | `fc.dictionary(fc.string(), fc.integer({ min: 0 }))` |

### Unit Tests (Example-Based)

- `TopBar` renders page title from pathname, no subtitle text
- `Sidebar` renders all 8 nav items with correct hrefs
- `InferencePanel` shows `"—"` when `totalRequests === 0`
- `CachePanel` renders donut when rate > 0 and requests > 0
- `QueuePanel` shows green empty state when all zeros
- `MonitoringPage` shows `"No data"` / `"No requests"` for null stats
- `PlaygroundPage` shows skeleton on loading, `"0 req"` on zero count, `"—"` on error
- `SettingsPage` shows `"Not configured"` for missing fields, shows Runtime Stats section

### Integration Tests

- Dashboard page loads and renders all four panels with mocked API responses
- Settings page renders with parallel health + stats + inference data
- Monitoring page renders with null stats (all empty states visible)
- Each page shows amber error banner when model service is unreachable

### TypeScript Compilation

Running `tsc --noEmit` with `strict: true` serves as a smoke test for:
- No `(data as any)` casts in core data paths
- All typed interfaces used correctly
- `unknown` + type guards for genuinely optional fields
