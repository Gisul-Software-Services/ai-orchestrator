# Implementation Plan: Frontend Production Redesign

## Overview

Incremental implementation of the Gisul Admin Console production redesign. Tasks proceed from foundational type/config changes through hook updates, new API routes, panel redesigns, page fixes, and finally property-based tests. Each step builds on the previous so no code is left orphaned.

## Tasks

- [x] 1. Update TypeScript types in `types/api.ts`
  - [x] 1.1 Add standalone `GpuMetrics` exported interface with fields: `available` (boolean), `error` (string | null, optional), `gpu_util_percent`, `memory_used_percent`, `memory_used_mb`, `memory_total_mb`, `temperature_c`, `power_watts` (all optional numbers)
    - _Requirements: 15.2_
  - [x] 1.2 Add standalone `QueuesMetrics` exported interface with fields: `active_jobs` (number), `jobs_in_store` (number), `queue_depths` (Record<string, number>)
    - _Requirements: 15.3_
  - [x] 1.3 Add `InferenceMetrics` exported interface with all confirmed fields: `total_requests`, `cache_hits`, `cache_misses`, `cache_hit_rate_percent`, `requests_by_endpoint`, `errors`, `batches_processed`, `avg_batch_size`, `total_generation_time_seconds`, `server_start_time` (string | null)
    - _Requirements: 15.1_
  - [x] 1.4 Update `MetricsOverview` to reference `GpuMetrics` for its `gpu` field instead of duplicating the field list inline
    - _Requirements: 15.4_
  - [x] 1.5 Remove `server_start_time` from `StatsResponse` type
    - _Requirements: 15.5_

- [x] 2. Update `hooks/useMetrics.ts` — type the three metric hooks
  - [x] 2.1 Type `useMetricsGpuQuery` to use `adminFetchJson<GpuMetrics>`
    - _Requirements: 15.6_
  - [x] 2.2 Type `useMetricsQueuesQuery` to use `adminFetchJson<QueuesMetrics>`
    - _Requirements: 15.7_
  - [x] 2.3 Type `useMetricsInferenceQuery` to use `adminFetchJson<InferenceMetrics>`
    - _Requirements: 15.8_

- [x] 3. Checkpoint — ensure TypeScript compiles with no errors after type changes
  - Ensure all type errors are resolved before proceeding. Ask the user if questions arise.

- [x] 4. Add `darkMode: 'class'` to `tailwind.config.ts`
  - Add `darkMode: 'class'` at the top level of the config object
  - _Requirements: 1.1_

- [x] 5. Create `app/page.tsx` — root redirect to `/dashboard`
  - Create a server component (no `"use client"`) that calls `redirect('/dashboard')` from `next/navigation`
  - _Requirements: 2.1, 2.2_

- [-] 6. Update `Sidebar.tsx` and delete `AppSidebar.tsx`
  - [x] 6.1 Update `Sidebar.tsx` with dark-first styles: `bg-zinc-950/95` background, `border-zinc-800/80` border, active item `bg-zinc-800/90 text-white ring-1 ring-zinc-700/60`, remove `dark:` prefix variants from base styles
    - _Requirements: 1.3, 3.2_
  - [x] 6.2 Add cyan active indicator dot: `h-1.5 w-1.5 rounded-full bg-console-accent shadow-[0_0_8px_rgba(34,211,238,0.8)]`
    - _Requirements: 3.2_
  - [x] 6.3 Add icon colour transitions: `text-console-accent` when active, `text-zinc-600 group-hover:text-zinc-400` otherwise
    - _Requirements: 3.2_
  - [x] 6.4 Ensure all 8 navigation items are present: Overview, Playground, Monitoring, Usage & Billing, Orgs & Keys, RAG Management, History, Settings
    - _Requirements: 3.3_
  - [x] 6.5 Retain model status dot using `useHealthQuery`: `bg-emerald-400` when loaded, `bg-red-400` when not loaded, `bg-zinc-500` when unreachable
    - _Requirements: 3.4_
  - [ ] 6.6 Delete `AppSidebar.tsx` from the codebase
    - _Requirements: 3.1_

- [ ] 7. Create `app/api/admin/settings/route.ts` — aggregation route
  - Fetch `/health`, `/stats`, and `/api/v1/metrics/overview` in parallel using `Promise.all`
  - Use the existing `proxyUtils` auth pattern (session cookie + `X-Api-Key`)
  - Return `{ source: "derived", data: { health, stats, overview } }` on success
  - Return 503 JSON `{ error: "..." }` if any upstream call fails
  - _Requirements: 8.1, 8.7_

- [ ] 8. Redesign `GpuPanel.tsx`
  - [ ] 8.1 Update props interface to `{ gpu: GpuMetrics | null; inference: InferenceMetrics | null; loading: boolean; unreachable: boolean }`
    - _Requirements: 4.1, 4.2_
  - [ ] 8.2 Implement 4-column grid layout (`grid-cols-1 md:grid-cols-4`) with cards: Model Status, VRAM, Temperature, GPU Util
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [ ] 8.3 VRAM card: Recharts donut (`innerRadius=40`, `outerRadius=56`) using `memory_used_percent`, cyan fill + zinc-800 background; display `X.XX / Y.YY GB` text below
    - _Requirements: 10.1, 10.2_
  - [ ] 8.4 Temperature card: display `temperature_c` with colour coding (`text-emerald-400` < 70°C, `text-amber-400` 70–84°C, `text-red-400` ≥ 85°C); display `power_watts` as `X W` subtitle when present
    - _Requirements: 10.3, 10.5_
  - [ ] 8.5 GPU Util card: display `gpu_util_percent` with colour coding (`text-cyan-400` < 90%, `text-amber-400` ≥ 90%)
    - _Requirements: 10.4_
  - [ ] 8.6 Model Status card: `model_loaded` badge + uptime derived from `inference.server_start_time` using `formatDistanceStrict`; omit uptime subtitle when `server_start_time` is null or unparseable
    - _Requirements: 4.4, 4.5_
  - [ ] 8.7 When `gpu.available === false`: render single "GPU unavailable" card spanning all 4 columns showing `gpu.error`; do not render donut or bar charts
    - _Requirements: 4.3, 10.6_
  - [ ] 8.8 Render skeleton placeholders when `loading` is true; render amber error card when `unreachable` is true
    - _Requirements: 14.1, 14.2_

- [ ] 9. Redesign `QueuePanel.tsx`
  - [ ] 9.1 Update props interface to `{ loading: boolean; error: boolean; lastOkAt: number | null; queues: QueuesMetrics | null }`
    - _Requirements: 6.1_
  - [ ] 9.2 Render summary row with `active_jobs` and `jobs_in_store` counts above per-queue rows
    - _Requirements: 11.2_
  - [ ] 9.3 Render per-queue rows sorted by depth descending; each row: queue name + `Math.trunc(Number(v))` depth + status dot (`bg-emerald-400` for 0, `bg-amber-400` for 1–5, `bg-red-400` for ≥ 6)
    - _Requirements: 6.2, 11.1, 11.3_
  - [ ] 9.4 When all depths are 0, show all rows with green dots (no "no data" message); when `queue_depths` is empty object, show "No queues reported"
    - _Requirements: 6.3, 11.4_
  - [ ] 9.5 Render skeleton placeholders when `loading` is true; render amber error card with last-ok timestamp when `error` is true
    - _Requirements: 14.1, 14.2_

- [ ] 10. Redesign `CachePanel.tsx`
  - [ ] 10.1 Update props interface to `{ loading: boolean; error: boolean; lastOkAt: number | null; cacheHitRatePercent: number | null; hits: number | null; misses: number | null }`
    - _Requirements: 7.1_
  - [ ] 10.2 Implement donut chart (`PieChart`, `innerRadius=40`, `outerRadius=56`) with hit segment (`#22d3ee`) and miss segment (`#27272a`); segments computed as `[Math.max(0, rate), Math.max(0, 100 - rate)]` where `rate = cacheHitRatePercent ?? 0`
    - _Requirements: 13.1, 13.4_
  - [ ] 10.3 Overlay `cache_hit_rate_percent` as a percentage label absolutely centred inside the donut using `relative` wrapper + `absolute inset-0 flex items-center justify-center`
    - _Requirements: 13.2_
  - [ ] 10.4 Display `hits` and `misses` as formatted integers below the chart; display `0` when null
    - _Requirements: 7.3, 13.3_
  - [ ] 10.5 When `cacheHitRatePercent` is null or 0, render fully grey donut and display `0.00%`
    - _Requirements: 7.2, 13.4_
  - [ ] 10.6 Render skeleton placeholders when `loading` is true; render amber error card when `error` is true
    - _Requirements: 14.1, 14.2_

- [ ] 11. Redesign `InferencePanel.tsx`
  - [ ] 11.1 Compute `avgLatencySeconds = total_generation_time_seconds / total_requests`; display `—` when `total_requests` is 0 or absent; display as `X.XXXs` otherwise
    - _Requirements: 5.1, 5.2, 12.2_
  - [ ] 11.2 Compute `errorRatePercent = Math.min(100, Math.max(0, (errors / total_requests) * 100))`; display `0.00%` when `total_requests` is 0
    - _Requirements: 5.3, 12.2_
  - [ ] 11.3 Render 3-stat grid: avg latency, total requests (formatted with `toLocaleString()`), error rate
    - _Requirements: 12.2_
  - [ ] 11.4 Render top-endpoints table: top 8 entries from `requests_by_endpoint` sorted descending; each row has endpoint name, request count, and a relative usage bar (`width: (count / maxCount) * 100%`, track `bg-zinc-800`, fill `bg-cyan-500/20`)
    - _Requirements: 12.1, 12.4_
  - [ ] 11.5 When `requests_by_endpoint` is empty or null, display "No endpoint data yet"
    - _Requirements: 12.3_
  - [ ] 11.6 Render skeleton placeholders when loading; render amber error card when error
    - _Requirements: 14.1, 14.2_

- [ ] 12. Checkpoint — verify all four panels render correctly with mocked data
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Update `app/dashboard/page.tsx`
  - [ ] 13.1 Add `useMetricsGpuQuery` call alongside existing queries; pass `gpuQ.data` and `inferenceQ.data` to `GpuPanel`
    - _Requirements: 4.1_
  - [ ] 13.2 Pass `queuesQ.data` to `QueuePanel` only when `queuesQ.isSuccess` is true
    - _Requirements: 6.4_
  - [ ] 13.3 Pass `cacheHitRatePercent`, `hits`, and `misses` from `inferenceQ.data` to `CachePanel`
    - _Requirements: 7.1_
  - [ ] 13.4 Pass `inferenceQ.data` to `InferencePanel` with correct field names
    - _Requirements: 5.1, 5.4_
  - [ ] 13.5 Pass `loading` and `unreachable` props derived from each query's `isLoading` and `isError` state to each panel
    - _Requirements: 14.1, 14.2_

- [ ] 14. Rewrite `app/settings/page.tsx`
  - [ ] 14.1 Replace all phantom field reads with only confirmed `HealthResponse` and `StatsResponse` fields
    - _Requirements: 8.1, 8.2_
  - [ ] 14.2 Add `useMetricsInferenceQuery` call; derive uptime from `InferenceMetrics.server_start_time`
    - _Requirements: 8.3_
  - [ ] 14.3 Render "Model" section: `model_loaded` badge, `memory_gb` formatted to 2 decimal places + "GB", GPU availability from `MetricsOverview.gpu.available`
    - _Requirements: 8.4_
  - [ ] 14.4 Render "Runtime Stats" section: `total_requests`, `cache_hit_rate_percent`, `avg_batch_size`, `batches_processed`, `errors`, uptime, current server time
    - _Requirements: 8.5_
  - [ ] 14.5 Render "Queue Snapshot" section: `queue_sizes` map from `HealthResponse` as name→depth rows
    - _Requirements: 8.6_
  - [ ] 14.6 Display informational banner when `source === "derived"`
    - _Requirements: 8.7_
  - [ ] 14.7 Render skeleton rows when loading; render red-bordered error card when query errors
    - _Requirements: 14.5, 14.6_

- [ ] 15. Fix `app/monitoring/page.tsx` — null field fixes
  - [ ] 15.1 Display `avg_batch_size` from `StatsResponse` formatted to 2 decimal places; display `0.00` when value is 0
    - _Requirements: 9.1_
  - [ ] 15.2 Display `total_requests` from `StatsResponse` as a formatted integer; display `0` when value is 0
    - _Requirements: 9.2_
  - [ ] 15.3 Compute `errorRate` from `InferenceMetrics.errors` and `InferenceMetrics.total_requests`; display `0.00%` when `total_requests` is 0
    - _Requirements: 9.3_
  - [ ] 15.4 Read `queue_depths` from `QueuesMetrics.queue_depths` (not a nested `queues.queue_depths` path)
    - _Requirements: 9.4_
  - [ ] 15.5 Add dismissible error banner when any query is in error state; retain last known chart data
    - _Requirements: 14.4_

- [ ] 16. Checkpoint — full dashboard and settings smoke test
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Write property-based tests using fast-check
  - [ ]* 17.1 Write property test for Property 1 — GPU field mapping correctness
    - Use `fc.record` with float fields to generate arbitrary `GpuMetrics` objects; render `GpuPanel` and assert displayed text matches formatted input values
    - **Property 1: GPU field mapping correctness**
    - **Validates: Requirements 4.2, 10.1, 10.2, 10.3, 10.4**
  - [ ]* 17.2 Write property test for Property 2 — Uptime is always non-negative
    - Use `fc.date({ max: new Date() })` to generate past dates; assert `Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))` is always ≥ 0
    - **Property 2: Uptime is always non-negative**
    - **Validates: Requirements 4.4**
  - [ ]* 17.3 Write property test for Property 3 — Error rate is always in [0, 100]
    - Use `fc.nat()` for errors and `fc.nat({ min: 1 })` for total_requests; assert clamped rate is in [0, 100]
    - **Property 3: Error rate is always in [0, 100]**
    - **Validates: Requirements 5.3**
  - [ ]* 17.4 Write property test for Property 4 — Average latency is non-negative
    - Use `fc.float({ min: 0 })` for total_generation_time_seconds and `fc.nat({ min: 1 })` for total_requests; assert result is ≥ 0 and finite
    - **Property 4: Average latency is non-negative when inputs are valid**
    - **Validates: Requirements 5.1**
  - [ ]* 17.5 Write property test for Property 5 — Cache donut segments always sum to 100
    - Use `fc.float({ min: 0, max: 100 })` for hit rate; assert hit + miss segments sum to exactly 100 (within floating-point tolerance)
    - **Property 5: Cache donut segments always sum to 100**
    - **Validates: Requirements 13.1, 7.1**
  - [ ]* 17.6 Write property test for Property 6 — Null metric fields never crash
    - Use `fc.record` with `fc.option(fc.float())` for each numeric field; assert rendering `GpuPanel` with any combination of null/undefined fields does not throw
    - **Property 6: Null/undefined metric fields never cause a crash**
    - **Validates: Requirements 4.3, 14.3**

- [ ] 18. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties using fast-check (minimum 100 runs each)
- Unit tests validate specific examples and edge cases
- All implementation is scoped to `frontend/web` — no backend changes required
