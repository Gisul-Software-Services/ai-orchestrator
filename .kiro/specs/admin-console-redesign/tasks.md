# Implementation Plan: Admin Console Redesign

## Overview

Surgical, production-ready fixes across the Gisul Admin Console. Each task targets a specific bug or polish gap identified in the requirements and design. No new dependencies are introduced. All test files go in `frontend/web/__tests__/` using Vitest + fast-check.

## Tasks

- [x] 1. Remove TopBar subtitle
  - In `components/layout/TopBar.tsx`, delete the `<p>` element that renders `"Internal admin console — authenticated staff only"`.
  - Keep the page title `<h1>`, the signed-in user badge, and the `ThemeToggle`.
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 2. Confirm AppSidebar.tsx is absent; verify Sidebar.tsx is the sole sidebar
  - Check `components/layout/` — `AppSidebar.tsx` does not exist (confirmed). No deletion needed.
  - Verify `app/layout.tsx` imports only `Sidebar` from `components/layout/Sidebar.tsx`.
  - _Requirements: 2.1, 2.2_

- [x] 3. Fix InferencePanel — rename prop and display latency in ms
  - In `components/dashboard/InferencePanel.tsx`:
    - Rename prop `avgLatencySeconds` → `avgLatencyMs`.
    - Replace `fmtSeconds` with `fmtMs(n) = typeof n === "number" ? \`${n.toFixed(0)} ms\` : "—"`.
    - Update the `<Stat>` call to use `fmtMs(avgLatencyMs)`.
  - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 3.1 Write property test for latency unit correctness
    - **Property 1: Latency unit correctness**
    - File: `frontend/web/__tests__/latency.test.ts`
    - Use `fc.float({ min: 0.001, max: 1000 })` for `totalGenSeconds` and `fc.integer({ min: 1, max: 100000 })` for `totalRequests`.
    - Assert `(totalGenSeconds / totalRequests) * 1000 > 0` and that `fmtMs` output ends with `" ms"`.
    - Tag: `// Feature: admin-console-redesign, Property 1: Latency unit correctness`
    - **Validates: Requirements 3.1**

- [x] 4. Fix dashboard/page.tsx — remove any-casts, compute latency in ms
  - Replace all `(inferenceQ.data as any)` casts with typed `const inferenceData: InferenceMetrics | undefined = inferenceQ.data`.
  - Replace `(queuesQ.data as any)` with `const queuesData: QueuesMetrics | undefined = queuesQ.data`.
  - Compute `avgLatencyMs = (inferenceData.total_generation_time_seconds / inferenceData.total_requests) * 1000`.
  - Pass `avgLatencyMs` (not `avgLatencySeconds`) to `<InferencePanel>`.
  - Remove the `(overviewQ.data as MetricsOverview | undefined)` cast — use the typed query directly.
  - _Requirements: 3.1, 15.1, 15.2_

- [x] 5. Fix GpuPanel — GPU unavailable state
  - In `components/dashboard/GpuPanel.tsx`:
    - When `gpu?.available === false`, set `value = "GPU unavailable"` and `subtitle = gpu?.error ?? "NVML not available"` and `indicatorColor = "zinc"` for all four GPU stat cards.
    - Remove the unused `differenceInSeconds` import.
    - Keep existing numeric display logic when `available === true`.
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.1 Write property test for GPU unavailable state
    - **Property 4: GPU unavailable state**
    - File: `frontend/web/__tests__/gpuPanel.test.ts`
    - Use `fc.string()` for the `error` field; generate `GpuMetrics` objects with `available: false`.
    - Assert that the derived display value equals `"GPU unavailable"` and that a non-empty `error` string appears as the subtitle.
    - Tag: `// Feature: admin-console-redesign, Property 4: GPU unavailable state`
    - **Validates: Requirements 4.1, 4.2**

- [x] 6. Fix CachePanel — empty state when no data
  - In `components/dashboard/CachePanel.tsx`:
    - Compute `isEmpty = (hits === null || hits === 0) && (misses === null || misses === 0)`.
    - When `isEmpty && !loading && !error`, render `"No cache data yet"` empty-state message instead of the `PieChart`.
    - Keep existing donut rendering when `isEmpty` is false.
  - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 6.1 Write property test for cache donut invariant
    - **Property 2: Cache donut invariant**
    - File: `frontend/web/__tests__/cachePanel.test.ts`
    - Use `fc.float({ min: 0, max: 100 })` for `cacheHitRatePercent`.
    - Assert `pieData[0].value + pieData[1].value === 100` and `pieData[0].value === cacheHitRatePercent`.
    - Tag: `// Feature: admin-console-redesign, Property 2: Cache donut invariant`
    - **Validates: Requirements 5.2**

  - [ ]* 6.2 Write property test for cache empty state
    - **Property 3: Cache empty state**
    - File: `frontend/web/__tests__/cachePanel.test.ts`
    - Use `fc.constantFrom(null, 0)` for both `hits` and `misses`.
    - Assert that `isEmpty(hits, misses)` returns `true` for all combinations.
    - Tag: `// Feature: admin-console-redesign, Property 3: Cache empty state`
    - **Validates: Requirements 5.1**

- [x] 7. Fix QueuePanel — empty state when all queues empty
  - In `components/dashboard/QueuePanel.tsx`:
    - Compute `isEmpty = Object.keys(queues?.queue_depths ?? {}).length === 0`.
    - When `isEmpty && !loading && !error`, replace the `"No queue data."` text with a styled empty state: green dot + `"All queues empty"` heading + `"No pending jobs"` subtitle.
    - Keep existing queue-depth rows when `isEmpty` is false, sorted descending by depth.
  - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 7.1 Write property test for queue sort order
    - **Property 10: Queue sort order**
    - File: `frontend/web/__tests__/queuePanel.test.ts`
    - Use `fc.dictionary(fc.string({ minLength: 1 }), fc.integer({ min: 0, max: 1000 }), { minKeys: 1 })`.
    - Assert that the rendered rows are in descending order of depth.
    - Tag: `// Feature: admin-console-redesign, Property 10: Queue sort order`
    - **Validates: Requirements 8.3**

- [x] 8. Checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Refactor useSettings hook — parallel queries, no /api/admin/settings
  - Rewrite `hooks/useSettings.ts` to fan out three parallel queries:
    - `useHealthQuery()` → `healthQ`
    - `useStatsQuery()` → `statsQ`
    - `useMetricsInferenceQuery()` → `inferenceQ`
  - Return `{ isLoading, isError, data: { source: "derived", data: { health, stats, inference } } }`.
  - Remove the old single `useQuery` call to `/api/admin/settings`.
  - Export the updated `SettingsPayload` type with typed `health`, `stats`, `inference` fields.
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 14.5_

- [x] 10. Redesign Settings page — typed data, all sections
  - Rewrite `app/settings/page.tsx` to consume the refactored `useSettingsQuery`:
    - Destructure `health: HealthResponse | null`, `stats: StatsResponse | null`, `inference: InferenceMetrics | null` from `q.data.data`.
    - Remove all `(health as any)`, `(stats as any)`, `(overview as any)` casts.
    - Add **Model Status** section: `model_loaded` → `"Loaded"` / `"Not loaded"`, `memory_gb`, `active_jobs`, `total_jobs_in_store`.
    - Add **Runtime Stats** section: `stats.total_requests`, `stats.cache_hit_rate_percent`, `stats.avg_batch_size`, `stats.batches_processed`, `stats.errors`.
    - Derive uptime from `inference?.server_start_time` using `formatDistanceStrict` from `date-fns`.
    - Replace all `"—"` fallbacks for missing config fields with `"Not configured"`.
    - Keep the amber derived-data banner.
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 15.2_

  - [ ]* 10.1 Write property test for settings uptime non-negative
    - **Property 6: Settings uptime non-negative**
    - File: `frontend/web/__tests__/settings.test.ts`
    - Use `fc.date({ max: new Date() })` for `server_start_time`.
    - Assert `Math.max(0, Math.floor((Date.now() - Date.parse(isoString)) / 1000)) >= 0` for all past dates.
    - Tag: `// Feature: admin-console-redesign, Property 6: Settings uptime non-negative`
    - **Validates: Requirements 6.2**

- [x] 11. Fix Monitoring page — null stats cards and cache empty state
  - In `app/monitoring/page.tsx`:
    - When `totalRequestsAllTime === null`: display `"No data"` with subtitle `"Stats endpoint unavailable"`.
    - When `avgBatchSize === null`: display `"No data"` with subtitle `"Stats endpoint unavailable"`.
    - When `cacheHitRateStats === null`: replace the donut with an empty-state message (no PieChart rendered).
    - When `errorRate === null`: display `"No requests"` instead of `"—"`.
    - Remove `(gpuQuery.data as any)` and `(inferenceQuery.data as any)` casts; use typed query data.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 15.2_

- [x] 12. Fix History page — number formatting in stats cards
  - In `app/history/page.tsx`:
    - Format `stats.total` as `stats.total.toLocaleString()`.
    - Format `stats.avgLatency` as `` `${stats.avgLatency} ms` ``.
    - Format `stats.errorRate` as `` `${stats.errorRate.toFixed(2)}%` ``.
  - _Requirements: 11.1, 11.2, 11.3_

  - [ ]* 12.1 Write property test for history total formatting
    - **Property 7: History total formatting**
    - File: `frontend/web/__tests__/history.test.ts`
    - Use `fc.integer({ min: 0, max: 10_000_000 })` for `total`.
    - Assert displayed value equals `total.toLocaleString()`.
    - Tag: `// Feature: admin-console-redesign, Property 7: History total formatting`
    - **Validates: Requirements 11.1**

  - [ ]* 12.2 Write property test for history latency formatting
    - **Property 8: History latency formatting**
    - File: `frontend/web/__tests__/history.test.ts`
    - Use `fc.float({ min: 0, max: 100000 })` for `avgLatency`.
    - Assert displayed value equals `` `${avgLatency} ms` ``.
    - Tag: `// Feature: admin-console-redesign, Property 8: History latency formatting`
    - **Validates: Requirements 11.2**

  - [ ]* 12.3 Write property test for history error rate formatting
    - **Property 9: History error rate formatting**
    - File: `frontend/web/__tests__/history.test.ts`
    - Use `fc.float({ min: 0, max: 100 })` for `errorRate`.
    - Assert displayed value equals `` `${errorRate.toFixed(2)}%` ``.
    - Tag: `// Feature: admin-console-redesign, Property 9: History error rate formatting`
    - **Validates: Requirements 11.3**

- [x] 13. Fix Playground page — loading skeleton, zero count, error state
  - In `app/playground/page.tsx`:
    - When `statsQ.isLoading`: render `<Skeleton className="h-3 w-10" />` in the badge.
    - When `statsQ.isError`: render `"—"` with `text-zinc-500` class.
    - When `statsQ.isSuccess && count === 0`: render `"0 req"` (not blank).
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 14. Checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Write Sidebar active-state property test
  - File: `frontend/web/__tests__/sidebar.test.ts`
  - Extract the active-detection logic (`pathname === href || pathname.startsWith(href + "/")`) into a pure helper function `getActiveHref(pathname, hrefs)`.
  - Use `fc.constantFrom(...NAV_HREFS)` for pathname.
  - Assert exactly one href is active for each pathname, and it is the most specific prefix match.
  - Tag: `// Feature: admin-console-redesign, Property 5: Sidebar active state uniqueness`
  - _Requirements: 2.5_

  - [ ]* 15.1 Write property-based test for sidebar active state
    - **Property 5: Sidebar active state uniqueness**
    - **Validates: Requirements 2.5**

- [x] 16. Run TypeScript type-check
  - Run `tsc --noEmit` in `frontend/web/` to confirm zero type errors across all modified files.
  - Fix any remaining `any` casts surfaced by the compiler in the core data paths.
  - _Requirements: 15.1, 15.2, 15.3_

- [x] 17. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- `tailwind.config.ts` already has `darkMode: "class"` — no change needed (Requirement 1 is already satisfied)
- `AppSidebar.tsx` does not exist — no deletion needed (Requirement 2.2 is already satisfied)
- Each task references specific requirements for traceability
- PBT tests use fast-check with minimum 100 iterations per property
- All test files go in `frontend/web/__tests__/`
