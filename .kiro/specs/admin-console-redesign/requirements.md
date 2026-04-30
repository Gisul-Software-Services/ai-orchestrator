# Requirements Document

## Introduction

The Gisul Admin Console is a Next.js 14 (App Router) + Tailwind + Recharts internal admin dashboard for an AI platform. The current implementation has several data-wiring bugs (null/empty fields, wrong units), a duplicate sidebar component, a missing `darkMode` config, and inconsistent UI polish across its eight pages (Dashboard, Playground, Monitoring, Usage & Billing, Orgs & Keys, RAG Management, History, Settings). This feature delivers a production-ready redesign that fixes all data issues, consolidates the sidebar, and brings every page to a consistent, polished standard while preserving the existing dark theme with cyan accent (`#22d3ee`).

## Glossary

- **Admin_Console**: The Next.js 14 frontend application at `frontend/web/`.
- **Dashboard**: The `/dashboard` page showing live GPU, inference, queue, and cache panels.
- **InferencePanel**: The `components/dashboard/InferencePanel.tsx` component displaying latency, request count, and error rate.
- **GpuPanel**: The `components/dashboard/GpuPanel.tsx` component displaying GPU VRAM, temperature, and utilisation stats.
- **CachePanel**: The `components/dashboard/CachePanel.tsx` component displaying cache hit rate as a donut chart.
- **QueuePanel**: The `components/dashboard/QueuePanel.tsx` component displaying queue depths and active jobs.
- **Sidebar**: The single consolidated sidebar component at `components/layout/Sidebar.tsx`.
- **TopBar**: The `components/layout/TopBar.tsx` sticky header component.
- **Settings_Page**: The `/settings` page displaying derived configuration from health and stats endpoints.
- **Monitoring_Page**: The `/monitoring` page showing live time-series charts.
- **History_Page**: The `/history` page showing paginated request logs.
- **Playground_Page**: The `/playground` index page and its sub-pages.
- **Model_Service**: The backend Python service proxied through Next.js API routes under `/api/admin/*`.
- **NVML**: NVIDIA Management Library; may be unavailable when no CUDA device is present.
- **StatsResponse**: The JSON shape returned by `/api/admin/stats` (`total_requests`, `cache_hit_rate_percent`, `requests_by_endpoint`, `batches_processed`, `avg_batch_size`, `errors`).
- **InferenceMetrics**: The JSON shape returned by `/api/admin/metrics/inference` including `total_generation_time_seconds` and `total_requests`.
- **HealthResponse**: The JSON shape returned by `/api/admin/health` (`status`, `model_loaded`, `memory_gb`, `queue_sizes`, `active_jobs`, `total_jobs_in_store`).
- **Tailwind_Config**: The file `frontend/web/tailwind.config.ts`.

---

## Requirements

### Requirement 1: Fix Tailwind Dark Mode Configuration

**User Story:** As a developer, I want dark mode to be correctly configured in Tailwind, so that all dark-mode utility classes apply reliably across the application.

#### Acceptance Criteria

1. THE Tailwind_Config SHALL include `darkMode: "class"` at the top level of the exported config object.
2. WHEN the `dark` class is present on the `<html>` element, THE Admin_Console SHALL apply all `dark:` variant utility classes correctly.

---

### Requirement 2: Consolidate Sidebar Components

**User Story:** As a developer, I want a single sidebar component, so that navigation is consistent and there is no dead code.

#### Acceptance Criteria

1. THE Admin_Console SHALL contain exactly one sidebar component used in `app/layout.tsx`.
2. WHEN `AppSidebar.tsx` exists as a separate file, THE Admin_Console SHALL remove or merge it into `Sidebar.tsx`.
3. THE Sidebar SHALL display navigation links for all eight pages: Dashboard, Playground, Monitoring, Usage & Billing, Orgs & Keys, RAG Management, History, and Settings.
4. THE Sidebar SHALL show a model-status indicator in its footer using data from the `/api/admin/health` endpoint.
5. WHEN a nav item is active, THE Sidebar SHALL highlight it with the `console-accent` colour and a glowing dot.

---

### Requirement 3: Fix Inference Latency Units

**User Story:** As an admin, I want the average latency displayed in milliseconds, so that I can accurately assess model response times.

#### Acceptance Criteria

1. WHEN `total_generation_time_seconds` and `total_requests` are both available from `InferenceMetrics`, THE InferencePanel SHALL compute average latency as `(total_generation_time_seconds / total_requests) * 1000` and display it in milliseconds (e.g. `"142 ms"`).
2. WHEN `total_requests` is zero or either value is unavailable, THE InferencePanel SHALL display `"—"` for average latency.
3. THE InferencePanel SHALL label the latency stat `"Avg latency"` with a `"ms"` suffix, not `"s"`.

---

### Requirement 4: Fix GPU Panel Null/Unavailable States

**User Story:** As an admin, I want the GPU panel to show a clear, informative state when NVML is unavailable, so that I understand why metrics are missing rather than seeing bare dashes.

#### Acceptance Criteria

1. WHEN `GpuMetrics.available` is `false`, THE GpuPanel SHALL display a labelled unavailable state (e.g. `"GPU unavailable"`) for each GPU stat card instead of `"—"`.
2. WHEN `GpuMetrics.error` is a non-empty string, THE GpuPanel SHALL display that error string as a subtitle beneath the unavailable label.
3. WHEN `GpuMetrics.available` is `true` and a numeric value is present, THE GpuPanel SHALL display the formatted value with its unit.
4. WHEN `GpuMetrics.available` is `true` but a specific field (e.g. `power_watts`) is `null`, THE GpuPanel SHALL display `"—"` for that field only.

---

### Requirement 5: Fix Cache Panel Empty State

**User Story:** As an admin, I want the cache panel to show a meaningful empty state when no requests have been made yet, so that I don't see a misleading 0%/100% donut chart.

#### Acceptance Criteria

1. WHEN `cacheHitRatePercent` is `null` and both `hits` and `misses` are `0` or `null`, THE CachePanel SHALL display an empty-state message (e.g. `"No cache data yet"`) instead of a donut chart.
2. WHEN `cacheHitRatePercent` is a valid number greater than `0`, THE CachePanel SHALL render the donut chart with the correct hit/miss split.
3. WHEN `cacheHitRatePercent` is `0` and total requests are greater than `0`, THE CachePanel SHALL render the donut chart showing a 0% hit rate.

---

### Requirement 6: Fix Settings Page Derived Data Display

**User Story:** As an admin, I want the Settings page to show meaningful values derived from available endpoints, so that I don't see a page full of `"—"` dashes.

#### Acceptance Criteria

1. THE Settings_Page SHALL derive `model_loaded` status from `HealthResponse.model_loaded` and display it as `"Loaded"` or `"Not loaded"`.
2. THE Settings_Page SHALL derive uptime from `StatsResponse.server_start_time` (if present) or `InferenceMetrics.server_start_time` and display it as a human-readable duration.
3. WHEN a configuration field is not available from any endpoint, THE Settings_Page SHALL display `"Not configured"` instead of `"—"`.
4. THE Settings_Page SHALL display a banner explaining that configuration is derived from health and stats endpoints when no dedicated settings endpoint is available.
5. THE Settings_Page SHALL display `HealthResponse.status`, `HealthResponse.model_loaded`, `HealthResponse.memory_gb`, `HealthResponse.active_jobs`, and `HealthResponse.total_jobs_in_store` in the appropriate sections.
6. WHEN `StatsResponse` is available, THE Settings_Page SHALL display `avg_batch_size`, `batches_processed`, `total_requests`, `errors`, and `cache_hit_rate_percent` in a Runtime Stats section.

---

### Requirement 7: Fix Monitoring Page Null Stats

**User Story:** As an admin, I want the Monitoring page stats cards to show contextual labels when data is unavailable, so that I understand the reason rather than seeing bare dashes.

#### Acceptance Criteria

1. WHEN `totalRequestsAllTime` is `null`, THE Monitoring_Page SHALL display `"No data"` with a subtitle `"Stats endpoint unavailable"` instead of `"—"`.
2. WHEN `avgBatchSize` is `null`, THE Monitoring_Page SHALL display `"No data"` with a subtitle `"Stats endpoint unavailable"` instead of `"—"`.
3. WHEN `cacheHitRateStats` is `null`, THE Monitoring_Page SHALL display an empty-state message in the cache hit rate card instead of rendering a 0/100 donut.
4. WHEN `errorRate` is `null` (no requests yet), THE Monitoring_Page SHALL display `"No requests"` instead of `"—"`.

---

### Requirement 8: Improve QueuePanel Empty State

**User Story:** As an admin, I want the queue panel to show a clear empty state with context when no queues are reported, so that I can distinguish between "no queues configured" and "data unavailable".

#### Acceptance Criteria

1. WHEN `queue_depths` is an empty object `{}`, THE QueuePanel SHALL display an empty-state message: `"All queues empty"` with a subtitle `"No pending jobs"`.
2. WHEN `active_jobs` is `0` and `jobs_in_store` is `0` and `queue_depths` is empty, THE QueuePanel SHALL show the empty state with a green indicator.
3. WHEN at least one queue has a depth greater than `0`, THE QueuePanel SHALL display each queue name and depth sorted descending by depth.

---

### Requirement 9: Remove Redundant TopBar Subtitle

**User Story:** As an admin, I want the TopBar to show only the current page title and user info, so that the interface is clean and not cluttered with repeated boilerplate text.

#### Acceptance Criteria

1. THE TopBar SHALL display the current page title derived from the URL pathname.
2. THE TopBar SHALL NOT display the subtitle `"Internal admin console — authenticated staff only"` on every page.
3. THE TopBar SHALL display the signed-in user label and the theme toggle.

---

### Requirement 10: Playground Page Meaningful Empty States

**User Story:** As an admin, I want the Playground index cards to show a clear empty state when request counts are zero, so that I can distinguish between "never used" and "loading".

#### Acceptance Criteria

1. WHEN `statsQ.isLoading` is `true`, THE Playground_Page SHALL display a skeleton in the request count badge.
2. WHEN a stat key has a count of `0` and `statsQ.isSuccess` is `true`, THE Playground_Page SHALL display `"0 req"` (not blank) in the badge.
3. WHEN `statsQ.isError` is `true`, THE Playground_Page SHALL display `"—"` in the badge with a muted style.

---

### Requirement 11: History Page Stats Formatting

**User Story:** As an admin, I want the History page stats cards to display formatted numbers, so that large values are readable.

#### Acceptance Criteria

1. THE History_Page SHALL format `stats.total` using `toLocaleString()` (e.g. `"1,234"`).
2. THE History_Page SHALL format `stats.avgLatency` as `"142 ms"` with the `ms` unit label.
3. THE History_Page SHALL format `stats.errorRate` to two decimal places followed by `%`.

---

### Requirement 12: Full-Page Loading Skeleton on First Load

**User Story:** As an admin, I want to see a loading skeleton on first page load, so that the layout doesn't jump from empty to populated.

#### Acceptance Criteria

1. WHEN all data queries for a page are in the `isLoading` state simultaneously, THE Dashboard SHALL display skeleton placeholders for each panel.
2. WHEN at least one query has returned data, THE Dashboard SHALL render available panels and show skeletons only for panels still loading.
3. THE Skeleton component SHALL use the existing `components/ui/skeleton.tsx` implementation.

---

### Requirement 13: Consistent Design System

**User Story:** As an admin, I want all panels and pages to use a consistent visual language, so that the console looks production-ready.

#### Acceptance Criteria

1. THE Admin_Console SHALL use `border-zinc-800` and `bg-zinc-950/60` as the standard panel surface across all dashboard panels.
2. THE Admin_Console SHALL use `text-console-accent` (`#22d3ee`) for active nav items, chart lines, and primary action buttons.
3. THE Admin_Console SHALL use `rounded-xl` for all panel containers.
4. WHEN displaying error states, THE Admin_Console SHALL use `border-amber-500/30 bg-amber-500/10 text-amber-200` for warning banners.
5. WHEN displaying success/healthy states, THE Admin_Console SHALL use `text-emerald-400` or `bg-emerald-400` for status indicators.
6. THE Admin_Console SHALL apply consistent `space-y-6` vertical rhythm between page sections.

---

### Requirement 14: All Eight Pages Fully Functional

**User Story:** As an admin, I want every page in the console to load and display real data without errors, so that I can use the full feature set.

#### Acceptance Criteria

1. THE Dashboard SHALL display live data from `/api/admin/metrics/overview`, `/api/admin/metrics/inference`, `/api/admin/metrics/queues`, `/api/admin/health`, and `/api/admin/stats`.
2. THE Monitoring_Page SHALL display live time-series charts from `useMetricsHistory` and summary stats from `useStatsQuery`.
3. THE Playground_Page SHALL display endpoint cards with request counts from `useStatsQuery`.
4. THE History_Page SHALL display paginated request logs from `useRequestLogQuery`.
5. THE Settings_Page SHALL display derived configuration from `useHealthQuery`, `useStatsQuery`, and `useMetricsInferenceQuery`.
6. WHEN the Model_Service is unreachable, EACH page SHALL display a non-blocking error banner and continue to show the last known data where available.
7. THE Orgs_Page SHALL display organisations from `useOrgsListQuery`.
8. THE RAG_Page SHALL display index health from `useRagHealthQuery`.

---

### Requirement 15: No TypeScript `any` Casts in Core Data Paths

**User Story:** As a developer, I want the core data-fetching and display paths to use proper TypeScript types, so that the codebase is maintainable and type-safe.

#### Acceptance Criteria

1. THE Admin_Console SHALL define typed interfaces in `types/api.ts` for all data shapes returned by `/api/admin/*` routes that are currently typed as `any`.
2. WHEN accessing fields from `InferenceMetrics`, `GpuMetrics`, `HealthResponse`, or `StatsResponse`, THE Admin_Console SHALL use the typed interfaces rather than `(data as any).field` casts.
3. WHERE a backend field is genuinely optional or unknown, THE Admin_Console SHALL use `unknown` with a type-guard function rather than `any`.
