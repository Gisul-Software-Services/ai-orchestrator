# Design Document — Frontend Production Redesign

## Overview

The Gisul Admin Console is a Next.js 14 internal dashboard. This redesign addresses three categories of work:

1. **Field mapping correctness** — every panel reads fields from the correct API response shape, eliminating `—` values caused by mismatched field paths.
2. **Dark-theme enforcement** — the UI always renders in dark mode by default; no white flash, no `dark:` prefix required for base styles.
3. **Type safety** — `types/api.ts` is updated to reflect the actual backend shapes, and all hooks are typed accordingly.

The work is scoped entirely to the Next.js frontend (`frontend/web`). No backend changes are required except for the new `/api/admin/settings` aggregation route, which is a Next.js API route (not a backend change).

---

## Architecture

The application follows the standard Next.js 14 App Router pattern:

```
app/
  layout.tsx          ← root layout: ThemeProvider → QueryProvider → Sidebar + main
  page.tsx            ← NEW: redirect('/dashboard')
  dashboard/page.tsx  ← dashboard with all four panels
  settings/page.tsx   ← settings page (rewritten)
  monitoring/page.tsx ← monitoring page (field fixes only)
  api/admin/
    settings/route.ts ← NEW: aggregates health + stats + overview
    metrics/gpu/      ← existing proxy
    metrics/inference/← existing proxy
    metrics/queues/   ← existing proxy
    metrics/overview/ ← existing proxy
components/
  layout/
    Sidebar.tsx       ← updated: dark-first styles, AppSidebar patterns
    AppSidebar.tsx    ← DELETED
    ThemeProvider.tsx ← already correct (defaultTheme="dark")
  dashboard/
    GpuPanel.tsx      ← redesigned: 4-column grid with donut + bar
    QueuePanel.tsx    ← redesigned: summary row + per-queue rows
    CachePanel.tsx    ← redesigned: donut with centred label
    InferencePanel.tsx← redesigned: 3-stat grid + inline usage bars
hooks/
  useMetrics.ts       ← updated: typed hooks for GpuMetrics, QueuesMetrics, InferenceMetrics
types/
  api.ts              ← updated: new standalone types, removed phantom fields
```

Data flow for the dashboard:

```mermaid
graph TD
  A[DashboardPage] -->|useHealthQuery| B[/api/admin/health]
  A -->|useMetricsGpuQuery| C[/api/admin/metrics/gpu]
  A -->|useMetricsInferenceQuery| D[/api/admin/metrics/inference]
  A -->|useMetricsQueuesQuery| E[/api/admin/metrics/queues]
  A -->|useMetricsOverviewQuery| F[/api/admin/metrics/overview]
  A --> G[GpuPanel ← gpuQ.data + inferenceQ.data]
  A --> H[QueuePanel ← queuesQ.data]
  A --> I[CachePanel ← inferenceQ.data]
  A --> J[InferencePanel ← inferenceQ.data]
```

---

## Components and Interfaces

### 1. `types/api.ts` — Type Updates

**New standalone types:**

```ts
export interface GpuMetrics {
  available: boolean;
  error?: string | null;
  gpu_util_percent?: number;
  memory_used_percent?: number;
  memory_used_mb?: number;
  memory_total_mb?: number;
  temperature_c?: number;
  power_watts?: number | null;
}

export interface QueuesMetrics {
  active_jobs: number;
  jobs_in_store: number;
  queue_depths: Record<string, number>;
}

export interface InferenceMetrics {
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
```

**Updated `MetricsOverview`:** the `gpu` field references `GpuMetrics` instead of duplicating the field list.

**Updated `StatsResponse`:** remove `server_start_time` (does not exist in `/stats`).

### 2. `hooks/useMetrics.ts` — Hook Typing

`useMetricsGpuQuery` → `adminFetchJson<GpuMetrics>`  
`useMetricsQueuesQuery` → `adminFetchJson<QueuesMetrics>`  
`useMetricsInferenceQuery` → `adminFetchJson<InferenceMetrics>`

### 3. `tailwind.config.ts`

Add `darkMode: 'class'` at the top level of the config object. The `ThemeProvider` already sets `defaultTheme="dark"` and `attribute="class"`, so no ThemeProvider changes are needed.

### 4. `app/page.tsx` — Root Redirect

```ts
import { redirect } from 'next/navigation';
export default function RootPage() { redirect('/dashboard'); }
```

Server component; no `"use client"` directive. The existing middleware auth guard fires before this page renders, so the auth flow is preserved.

### 5. `Sidebar.tsx` — Dark-First Consolidation

- Remove `dark:` prefix variants from base styles; use dark-first values directly.
- Background: `bg-zinc-950/95`, border: `border-zinc-800/80`.
- Active item: `bg-zinc-800/90 text-white ring-1 ring-zinc-700/60`.
- Active indicator: cyan dot `h-1.5 w-1.5 rounded-full bg-console-accent shadow-[0_0_8px_rgba(34,211,238,0.8)]` (from AppSidebar).
- Icon: `text-console-accent` when active, `text-zinc-600 group-hover:text-zinc-400` otherwise.
- Logo block: gradient icon container from AppSidebar.
- Navigation items: all 8 from current `Sidebar.tsx` (Overview, Playground, Monitoring, Usage & Billing, Orgs & Keys, RAG Management, History, Settings).
- Model status dot: retained from current `Sidebar.tsx`, using `useHealthQuery`.

`AppSidebar.tsx` is deleted.

### 6. `GpuPanel.tsx` — Redesign

Props interface:

```ts
{
  gpu: GpuMetrics | null;
  inference: InferenceMetrics | null;
  loading: boolean;
  unreachable: boolean;
}
```

Layout: 4-column grid (`grid-cols-1 md:grid-cols-4`).

| Column | Card | Content |
|--------|------|---------|
| 1 | Model Status | `model_loaded` badge + uptime from `inference.server_start_time` |
| 2 | VRAM | Recharts donut (`memory_used_percent`) + `X.XX / Y.YY GB` text |
| 3 | Temperature | `temperature_c` with colour coding + `power_watts` subtitle |
| 4 | GPU Util | `gpu_util_percent` with colour coding |

Colour rules:
- Temperature: `text-emerald-400` < 70°C, `text-amber-400` 70–84°C, `text-red-400` ≥ 85°C
- GPU util: `text-cyan-400` < 90%, `text-amber-400` ≥ 90%
- VRAM indicator dot: emerald < 70%, amber 70–89%, red ≥ 90%

When `gpu.available === false`: render a single "GPU unavailable" card spanning all 4 columns showing `gpu.error`.

Uptime calculation: `formatDistanceStrict(new Date(server_start_time), new Date())`. If `server_start_time` is null or `Date.parse` returns `NaN`, omit the subtitle entirely.

### 7. `QueuePanel.tsx` — Redesign

Props interface:

```ts
{
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  queues: QueuesMetrics | null;
}
```

Layout:
1. Summary row: "Active jobs: N" and "Jobs in store: N" side by side.
2. Per-queue rows sorted by depth descending. Each row: queue name + depth count + status dot.
   - Depth 0 → `bg-emerald-400`
   - Depth 1–5 → `bg-amber-400`
   - Depth ≥ 6 → `bg-red-400`
3. When all depths are 0, show all rows with green dots (no "no data" message).
4. When `queue_depths` is empty object, show "No queues reported."

Depth values are cast with `Math.trunc(Number(v))` before display to guard against string-typed values.

### 8. `CachePanel.tsx` — Redesign

Props interface:

```ts
{
  loading: boolean;
  error: boolean;
  lastOkAt: number | null;
  cacheHitRatePercent: number | null;
  hits: number | null;
  misses: number | null;
}
```

Layout: donut chart (Recharts `PieChart`, `innerRadius=40`, `outerRadius=56`) with the percentage value absolutely centred inside using a `relative` wrapper and `absolute inset-0 flex items-center justify-center` overlay.

Pie data:
```ts
[
  { name: 'Hit',  value: Math.max(0, rate) },
  { name: 'Miss', value: Math.max(0, 100 - rate) },
]
```
Where `rate = cacheHitRatePercent ?? 0`. This guarantees the two segments always sum to 100.

Hit colour: `#22d3ee` (cyan). Miss colour: `#27272a` (zinc-800).

Hits and misses displayed as integers below the chart. When null, display `0`.

### 9. `InferencePanel.tsx` — Redesign

Props interface unchanged. Internal changes:

- Top-endpoints table replaces `EndpointBarChart`. Shows top 8 entries from `requestsByEndpoint` sorted descending.
- Each row has a relative usage bar: `width: (count / maxCount) * 100%`, track `bg-zinc-800`, fill `bg-cyan-500/20`.
- Stat grid: avg latency formatted as `X.XXXs`, total requests as `toLocaleString()`, error rate as `X.XX%`.
- When `requestsByEndpoint` is empty/null: "No endpoint data yet" message.

### 10. `app/settings/page.tsx` — Rewrite

Data sources:
- `useHealthQuery()` → `HealthResponse` fields only
- `useStatsQuery()` → `StatsResponse` fields only
- `useMetricsInferenceQuery()` → `server_start_time` for uptime
- `useMetricsOverviewQuery()` → `gpu.available` for GPU status

Sections:

| Section | Fields |
|---------|--------|
| Model | `model_loaded` (badge), `memory_gb` (X.XX GB), GPU available (from overview) |
| Runtime Stats | `total_requests`, `cache_hit_rate_percent`, `avg_batch_size`, `batches_processed`, `errors`, uptime, current time |
| Queue Snapshot | `queue_sizes` map from HealthResponse as name→depth rows |

All phantom fields removed. `source: "derived"` banner retained.

### 11. `app/api/admin/settings/route.ts` — New Route

Aggregates three upstream calls in parallel:

```ts
const [health, stats, overview] = await Promise.all([
  fetch(gatewayBase + '/health', ...),
  fetch(gatewayBase + '/stats', ...),
  fetch(gatewayBase + '/api/v1/metrics/overview', ...),
]);
```

Returns:
```ts
{
  source: "derived",
  data: { health, stats, overview }
}
```

Uses the existing `proxyUtils` auth pattern (session cookie + `X-Api-Key`). If any upstream call fails, returns a 503 with an error message.

---

## Data Models

### `SettingsPayload` (hook type, already defined in `useSettings.ts`)

```ts
type SettingsPayload = {
  source: "settings-endpoint" | "derived";
  data: {
    health: HealthResponse;
    stats: StatsResponse;
    overview: MetricsOverview;
  };
};
```

### Uptime Calculation

```ts
function formatUptime(serverStartTime: string | null | undefined): string | null {
  if (!serverStartTime) return null;
  const parsed = Date.parse(serverStartTime);
  if (Number.isNaN(parsed)) return null;
  const seconds = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  // format as "Xd Xh Xm Xs" or use date-fns formatDistanceStrict
  return formatDistanceStrict(new Date(parsed), new Date()).replace(' ago', '').trim();
}
```

The `Math.max(0, ...)` clamp ensures the result is never negative even if clocks are slightly skewed.

### Error Rate Calculation

```ts
function calcErrorRate(errors: number, totalRequests: number): number | null {
  if (totalRequests <= 0) return null;
  return Math.min(100, Math.max(0, (errors / totalRequests) * 100));
}
```

Clamped to `[0, 100]` to handle any floating-point edge cases.

### Cache Donut Segments

```ts
const rate = cacheHitRatePercent ?? 0;
const segments = [
  { name: 'Hit',  value: Math.max(0, Math.min(100, rate)) },
  { name: 'Miss', value: Math.max(0, Math.min(100, 100 - rate)) },
];
// Invariant: segments[0].value + segments[1].value === 100
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: GPU field mapping correctness

*For any* `GpuMetrics` object with numeric fields, when `GpuPanel` renders with that object as its `gpu` prop, the displayed text for `gpu_util_percent`, `memory_used_percent`, `memory_used_mb`, `memory_total_mb`, and `temperature_c` must exactly match the values from the input object (formatted per the display rules).

**Validates: Requirements 4.2, 10.1, 10.2, 10.3, 10.4**

### Property 2: Uptime is always non-negative

*For any* ISO 8601 datetime string representing a point in the past, the uptime duration computed from `server_start_time` to `Date.now()` must be a non-negative number of seconds.

**Validates: Requirements 4.4**

### Property 3: Error rate is always in [0, 100]

*For any* non-negative integer `errors` and positive integer `total_requests`, the computed `errorRatePercent = (errors / total_requests) * 100` clamped to `[0, 100]` must satisfy `0 ≤ errorRatePercent ≤ 100`.

**Validates: Requirements 5.3**

### Property 4: Average latency is non-negative when inputs are valid

*For any* non-negative `total_generation_time_seconds` and positive `total_requests`, the computed `avgLatencySeconds = total_generation_time_seconds / total_requests` must be a non-negative finite number.

**Validates: Requirements 5.1**

### Property 5: Cache donut segments always sum to 100

*For any* `cache_hit_rate_percent` value in `[0, 100]`, the hit segment value plus the miss segment value in the donut chart data must equal exactly 100.

**Validates: Requirements 13.1, 7.1**

### Property 6: Null/undefined metric fields never cause a crash — display fallback

*For any* `GpuMetrics` object where any numeric field is `null` or `undefined`, rendering `GpuPanel` must not throw and must display `"—"` or `"0"` in place of the missing value (never `NaN`, `undefined`, or a React render error).

**Validates: Requirements 4.3, 14.3**

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Any metrics query returns HTTP error | Panel renders amber error card with "Could not reach model-service" + last-ok timestamp |
| `gpu.available === false` | GpuPanel renders single "GPU unavailable" message with `gpu.error` string |
| `server_start_time` is null or unparseable | Uptime subtitle is omitted; no crash |
| `total_requests === 0` | Avg latency and error rate display `—` / `0.00%` respectively |
| `queue_depths` is empty object | QueuePanel shows "No queues reported" |
| `cache_hit_rate_percent` is null | Donut renders as 100% miss (full grey); label shows `0.00%` |
| Settings query loading | Skeleton rows rendered in place of config values |
| Settings query error | Red-bordered error card: "Service unreachable" |
| `/api/admin/settings` upstream failure | Route returns 503 JSON `{ error: "..." }` |

---

## Testing Strategy

### Unit / Example Tests

- `app/page.tsx`: assert `redirect('/dashboard')` is called.
- `Sidebar.tsx`: render with each health state (loaded / not loaded / unreachable), assert status dot colour class.
- `GpuPanel.tsx`: render with `available=false`, assert error message shown; render with `available=true` and all fields null, assert `"—"` displayed.
- `CachePanel.tsx`: render with `cacheHitRatePercent=0`, assert donut data sums to 100 and label shows `0.00%`.
- `InferencePanel.tsx`: render with `requestsByEndpoint=null`, assert "No endpoint data yet" message.
- `QueuePanel.tsx`: render with empty `queue_depths`, assert "No queues reported"; render with all depths 0, assert green dots.
- `settings/page.tsx`: render with `source="derived"`, assert informational banner present.

### Property-Based Tests

Use [fast-check](https://github.com/dubzzz/fast-check) (TypeScript-native PBT library). Each property test runs a minimum of 100 iterations.

**Property 1 — GPU field mapping correctness**
```
// Feature: frontend-production-redesign, Property 1: GPU field mapping correctness
fc.assert(fc.property(
  fc.record({ gpu_util_percent: fc.float(), memory_used_percent: fc.float(), ... }),
  (gpuMetrics) => {
    render(<GpuPanel gpu={gpuMetrics} ... />);
    expect(screen.getByText(`${gpuMetrics.gpu_util_percent.toFixed(0)}%`)).toBeInTheDocument();
    // ... assert other fields
  }
), { numRuns: 100 });
```

**Property 2 — Uptime is always non-negative**
```
// Feature: frontend-production-redesign, Property 2: Uptime is always non-negative
fc.assert(fc.property(
  fc.date({ max: new Date() }),  // any past date
  (pastDate) => {
    const seconds = Math.max(0, Math.floor((Date.now() - pastDate.getTime()) / 1000));
    expect(seconds).toBeGreaterThanOrEqual(0);
  }
), { numRuns: 100 });
```

**Property 3 — Error rate is always in [0, 100]**
```
// Feature: frontend-production-redesign, Property 3: Error rate is always in [0, 100]
fc.assert(fc.property(
  fc.nat(),           // errors >= 0
  fc.nat({ min: 1 }), // total_requests > 0
  (errors, totalRequests) => {
    const rate = Math.min(100, Math.max(0, (errors / totalRequests) * 100));
    expect(rate).toBeGreaterThanOrEqual(0);
    expect(rate).toBeLessThanOrEqual(100);
  }
), { numRuns: 100 });
```

**Property 4 — Average latency is non-negative**
```
// Feature: frontend-production-redesign, Property 4: Average latency is non-negative
fc.assert(fc.property(
  fc.float({ min: 0 }),  // total_generation_time_seconds >= 0
  fc.nat({ min: 1 }),    // total_requests > 0
  (totalGenSeconds, totalRequests) => {
    const avg = totalGenSeconds / totalRequests;
    expect(avg).toBeGreaterThanOrEqual(0);
    expect(Number.isFinite(avg)).toBe(true);
  }
), { numRuns: 100 });
```

**Property 5 — Cache donut segments always sum to 100**
```
// Feature: frontend-production-redesign, Property 5: Cache donut segments always sum to 100
fc.assert(fc.property(
  fc.float({ min: 0, max: 100 }),
  (hitRate) => {
    const hit  = Math.max(0, Math.min(100, hitRate));
    const miss = Math.max(0, Math.min(100, 100 - hitRate));
    expect(hit + miss).toBeCloseTo(100, 10);
  }
), { numRuns: 100 });
```

**Property 6 — Null metric fields never crash**
```
// Feature: frontend-production-redesign, Property 6: Null metric fields never crash
fc.assert(fc.property(
  fc.record({
    available: fc.constant(true),
    gpu_util_percent: fc.option(fc.float()),
    memory_used_percent: fc.option(fc.float()),
    temperature_c: fc.option(fc.float()),
  }),
  (gpuMetrics) => {
    expect(() => render(<GpuPanel gpu={gpuMetrics} inference={null} loading={false} unreachable={false} />))
      .not.toThrow();
  }
), { numRuns: 100 });
```

### Integration Tests

- `GET /api/admin/settings`: call the route handler with a mocked upstream, assert the response shape matches `SettingsPayload`.
- Dashboard page: render with all queries mocked to success, assert all four panels are present and no error cards are shown.
