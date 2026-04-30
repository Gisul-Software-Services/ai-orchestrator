# Requirements Document

## Introduction

This document covers the production redesign of the Gisul Admin Console — a Next.js 14 internal dashboard for the Gisul AI Platform. The redesign addresses three categories of work: (1) fixing all null/`—` field mappings caused by mismatches between frontend field reads and actual backend API response shapes, (2) enforcing a consistent dark-theme production aesthetic across all pages, and (3) ensuring every page and API route is fully functional with proper loading, error, and empty states.

The backend exposes the following confirmed API shapes (verified from source):

- `GET /health` → `{ status, model_loaded, memory_gb, queue_sizes, active_jobs, total_jobs_in_store }`
- `GET /stats` → `{ total_requests, cache_hit_rate_percent, requests_by_endpoint, batches_processed, avg_batch_size, errors }` — **no** `server_start_time`
- `GET /api/v1/metrics/gpu` → `{ available, error, gpu_util_percent, memory_used_percent, memory_used_mb, memory_total_mb, temperature_c, power_watts }`
- `GET /api/v1/metrics/inference` → `{ total_requests, cache_hits, cache_misses, cache_hit_rate_percent, requests_by_endpoint, errors, batches_processed, avg_batch_size, total_generation_time_seconds, server_start_time }`
- `GET /api/v1/metrics/queues` → `{ active_jobs, jobs_in_store, queue_depths: Record<string, number> }`
- `GET /api/v1/metrics/overview` → `{ model_loaded, cuda_memory_gb, gpu: {...}, inference: { total_requests, cache_hit_rate_percent, requests_by_endpoint }, queues: { active_jobs, jobs_in_store, queue_depths } }`

---

## Glossary

- **Console**: The Gisul Admin Console Next.js 14 application.
- **Dashboard**: The `/dashboard` page showing the live system overview.
- **GpuPanel**: The dashboard component displaying GPU hardware metrics.
- **QueuePanel**: The dashboard component displaying batch queue depths and job counts.
- **CachePanel**: The dashboard component displaying cache hit/miss statistics.
- **InferencePanel**: The dashboard component displaying inference latency, request counts, and endpoint breakdown.
- **Sidebar**: The single canonical sidebar component (`Sidebar.tsx`) used in the root layout.
- **ThemeProvider**: The component that manages light/dark theme switching.
- **MetricsOverview**: The TypeScript type representing the `/api/v1/metrics/overview` response.
- **InferenceMetrics**: The TypeScript type representing the `/api/v1/metrics/inference` response.
- **GpuMetrics**: The TypeScript type representing the `/api/v1/metrics/gpu` response.
- **QueuesMetrics**: The TypeScript type representing the `/api/v1/metrics/queues` response.
- **HealthResponse**: The TypeScript type representing the `/health` response.
- **StatsResponse**: The TypeScript type representing the `/stats` response.
- **SettingsPage**: The `/settings` page showing read-only derived configuration.
- **MonitoringPage**: The `/monitoring` page showing historical time-series charts.
- **Dark Theme**: The production visual style — `bg-zinc-950` background, `text-zinc-50` primary text, `#22d3ee` (cyan) accent, `border-zinc-800` borders.
- **LiveIndicator**: The small status badge component showing "Live" or "Degraded".
- **Uptime**: The duration since `server_start_time` as returned by `/api/v1/metrics/inference`.
- **AppSidebar**: The unused dead-code sidebar component (`AppSidebar.tsx`) that must be removed.

---

## Requirements

### Requirement 1: Dark Theme Enforcement

**User Story:** As an admin, I want the console to always render in dark theme by default, so that the UI matches the production aesthetic without requiring manual theme switching.

#### Acceptance Criteria

1. THE Console SHALL include `darkMode: 'class'` in `tailwind.config.ts` so that Tailwind dark-mode utilities are activated via the `dark` class on the `<html>` element.
2. THE ThemeProvider SHALL apply the `dark` class to the `<html>` element by default on first load when no stored preference exists.
3. THE Sidebar SHALL render with `bg-zinc-950/95` background and `border-zinc-800` border in all states, without relying solely on `dark:` variant classes for its base appearance.
4. THE Console layout SHALL use `bg-zinc-950` as the default body background so that pages without explicit background classes do not render with a white flash.

---

### Requirement 2: Root Route Redirect

**User Story:** As an admin, I want visiting `/` to automatically redirect to `/dashboard`, so that there is no blank or 404 page at the root.

#### Acceptance Criteria

1. WHEN a user navigates to `/`, THE Console SHALL redirect the user to `/dashboard`.
2. THE redirect SHALL be implemented as a Next.js page-level redirect (via `app/page.tsx` using `redirect()`) so that it works server-side without a client round-trip.
3. WHEN the user is unauthenticated and visits `/`, THE Console middleware SHALL redirect to `/login` before the root redirect fires, preserving the existing auth guard behaviour.

---

### Requirement 3: Sidebar Consolidation

**User Story:** As a developer, I want a single canonical sidebar component, so that there is no dead code and navigation changes only need to be made in one place.

#### Acceptance Criteria

1. THE Console SHALL remove `AppSidebar.tsx` from the codebase, as it is not referenced in any layout or page.
2. THE Sidebar SHALL adopt the dark-first visual style from `AppSidebar.tsx`: `bg-zinc-950/95` background, `border-zinc-800/80` border, cyan-accented active state indicator dot, and icon colour transitions on hover.
3. THE Sidebar SHALL include all navigation items currently present in `Sidebar.tsx`: Overview, Playground, Monitoring, Usage & Billing, Orgs & Keys, RAG Management, History, and Settings.
4. THE Sidebar SHALL display the model status dot using data from `useHealthQuery`, with `bg-emerald-400` when loaded, `bg-red-400` when not loaded, and `bg-zinc-500` when unreachable.

---

### Requirement 4: Fix GpuPanel Field Mappings

**User Story:** As an admin, I want the GPU panel to show real hardware metrics instead of `—`, so that I can monitor GPU health at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL call `useMetricsGpuQuery` (proxying `/api/v1/metrics/gpu`) in addition to `useMetricsOverviewQuery`, and pass the dedicated GPU response to `GpuPanel` as the authoritative source for GPU fields.
2. THE GpuPanel SHALL read `gpu_util_percent`, `memory_used_percent`, `memory_used_mb`, `memory_total_mb`, `temperature_c`, and `power_watts` from the `GpuMetrics` response shape, not from `MetricsOverview.gpu`.
3. WHEN `GpuMetrics.available` is `false`, THE GpuPanel SHALL display the `error` string from the response in place of metric values, rather than showing `—`.
4. THE GpuPanel SHALL derive uptime from `InferenceMetrics.server_start_time` (from `useMetricsInferenceQuery`), not from `overview.inference.server_start_time`, which does not exist in the `MetricsOverview` type.
5. IF `InferenceMetrics.server_start_time` is absent or unparseable, THEN THE GpuPanel SHALL omit the uptime subtitle rather than displaying `—` or an invalid date.

---

### Requirement 5: Fix InferencePanel Field Mappings

**User Story:** As an admin, I want the inference panel to show real latency and request counts, so that I can assess model performance without manual calculation.

#### Acceptance Criteria

1. THE InferencePanel SHALL compute `avgLatencySeconds` as `total_generation_time_seconds / total_requests` using fields from `InferenceMetrics`, where `total_generation_time_seconds` is the confirmed field name in the `/api/v1/metrics/inference` response.
2. WHEN `total_requests` is `0` or absent, THE InferencePanel SHALL display `—` for average latency rather than dividing by zero.
3. THE InferencePanel SHALL read `errors` from `InferenceMetrics.errors` and compute `errorRatePercent` as `(errors / total_requests) * 100`, clamped to `[0, 100]`.
4. THE InferencePanel SHALL read `requests_by_endpoint` from `InferenceMetrics.requests_by_endpoint` for the top-endpoints table, falling back to `MetricsOverview.inference.requests_by_endpoint` if the dedicated inference query has not yet resolved.

---

### Requirement 6: Fix QueuePanel Field Mappings

**User Story:** As an admin, I want the queue panel to show accurate queue depths and job counts, so that I can detect backlogs immediately.

#### Acceptance Criteria

1. THE QueuePanel SHALL read `active_jobs`, `jobs_in_store`, and `queue_depths` from the `QueuesMetrics` response shape returned by `useMetricsQueuesQuery`, which proxies `/api/v1/metrics/queues`.
2. THE QueuePanel SHALL cast each value in `queue_depths` to an integer before display, guarding against string-typed values from the API.
3. WHEN `queue_depths` is an empty object, THE QueuePanel SHALL display a "No queues reported" message rather than an empty list.
4. THE Dashboard SHALL pass the raw `queuesQ.data` object directly to `QueuePanel` only after `queuesQ.isSuccess` is true, so that stale or undefined data is never rendered as zeros.

---

### Requirement 7: Fix CachePanel Field Mappings

**User Story:** As an admin, I want the cache panel to show real hit/miss counts, so that I can evaluate caching effectiveness.

#### Acceptance Criteria

1. THE CachePanel SHALL read `cache_hits`, `cache_misses`, and `cache_hit_rate_percent` from `InferenceMetrics` (via `useMetricsInferenceQuery`), which are confirmed fields in the `/api/v1/metrics/inference` response.
2. WHEN `cache_hit_rate_percent` is `null` or the query has not resolved, THE CachePanel SHALL render the donut chart with a full "miss" segment (100% grey) rather than an empty or broken chart.
3. THE CachePanel SHALL display `hits` and `misses` as formatted integers; WHEN either value is `null`, THE CachePanel SHALL display `0` rather than `—`, since the backend always returns these fields.

---

### Requirement 8: Fix Settings Page to Use Only Real API Fields

**User Story:** As an admin, I want the settings page to only show fields that actually exist in the API responses, so that I don't see a page full of `—` values.

#### Acceptance Criteria

1. THE SettingsPage SHALL only display fields that are confirmed to exist in `HealthResponse` (`status`, `model_loaded`, `memory_gb`, `queue_sizes`, `active_jobs`, `total_jobs_in_store`) or `StatsResponse` (`total_requests`, `cache_hit_rate_percent`, `requests_by_endpoint`, `batches_processed`, `avg_batch_size`, `errors`).
2. THE SettingsPage SHALL remove all references to non-existent `HealthResponse` fields: `model_name`, `quantization`, `batch_size_max`, `batch_timeout`, `cache_ttl`, `rate_limit_per_org_per_minute`, `aiml_catalog_path`, `aiml_faiss_path`, `dsa_enriched_path`, `dsa_faiss_path`, `allowed_origins`, `api_key_auth_enabled`, `org_verification_required`, `mongodb_uri`, `billing_db_name`, `organization_db_name`, `runtime_versions`, `docker_info`.
3. THE SettingsPage SHALL derive uptime from `InferenceMetrics.server_start_time` (from a dedicated `useMetricsInferenceQuery` call), not from `stats.server_start_time`, which does not exist in `StatsResponse`.
4. THE SettingsPage SHALL display a "Model" section showing: `model_loaded` (boolean badge), `memory_gb` (formatted to 2 decimal places with "GB" suffix), and GPU availability derived from `MetricsOverview.gpu.available`.
5. THE SettingsPage SHALL display a "Runtime Stats" section showing: `total_requests`, `cache_hit_rate_percent`, `avg_batch_size`, `batches_processed`, `errors`, uptime (derived from `server_start_time`), and current server time.
6. THE SettingsPage SHALL display a "Queue Snapshot" section showing the `queue_sizes` map from `HealthResponse` as a list of queue name → depth rows.
7. WHEN the settings query returns `source: "derived"`, THE SettingsPage SHALL display an informational banner stating that no dedicated settings endpoint exists and data is derived from health and stats snapshots.

---

### Requirement 9: Fix MonitoringPage Null Fields

**User Story:** As an admin, I want the monitoring page stats cards to show real values, so that I can assess system health without seeing `—` for fields that have data.

#### Acceptance Criteria

1. THE MonitoringPage SHALL display `avg_batch_size` from `StatsResponse` as a number formatted to 2 decimal places; WHEN `avg_batch_size` is `0`, THE MonitoringPage SHALL display `0.00` rather than `—`.
2. THE MonitoringPage SHALL display `total_requests` from `StatsResponse` as a formatted integer; WHEN the value is `0`, THE MonitoringPage SHALL display `0` rather than `—`.
3. THE MonitoringPage SHALL compute `errorRate` from `InferenceMetrics.errors` and `InferenceMetrics.total_requests`; WHEN `total_requests` is `0`, THE MonitoringPage SHALL display `0.00%` rather than `—`.
4. THE MonitoringPage SHALL read `queue_depths` from `QueuesMetrics.queue_depths` (the confirmed field name), not from a `queues.queue_depths` nested path that assumes a different response shape.

---

### Requirement 10: Dashboard Redesign — GPU Performance Panel

**User Story:** As an admin, I want the GPU panel to display utilisation and memory as visual gauges, so that I can assess GPU health at a glance without reading raw numbers.

#### Acceptance Criteria

1. THE GpuPanel SHALL display a VRAM utilisation donut chart using `memory_used_percent` from `GpuMetrics`, with a cyan fill segment and a zinc-800 background segment.
2. THE GpuPanel SHALL display a horizontal memory bar showing `memory_used_mb` and `memory_total_mb` as "X.XX / Y.YY GB", with a fill bar proportional to `memory_used_percent`.
3. THE GpuPanel SHALL display `temperature_c` as a numeric value with a colour indicator: `text-emerald-400` below 70°C, `text-amber-400` between 70°C and 85°C, and `text-red-400` at or above 85°C.
4. THE GpuPanel SHALL display `gpu_util_percent` as a numeric percentage with a colour indicator: `text-cyan-400` below 90%, `text-amber-400` at or above 90%.
5. WHEN `power_watts` is a number, THE GpuPanel SHALL display it formatted as `X W` alongside the temperature value.
6. WHEN `GpuMetrics.available` is `false`, THE GpuPanel SHALL replace all metric values with a single "GPU unavailable" message showing the `error` string, and SHALL NOT render the donut or bar charts.

---

### Requirement 11: Dashboard Redesign — Queue Panel with Per-Queue Rows

**User Story:** As an admin, I want the queue panel to show each queue as a labelled row with a depth count and status indicator, so that I can identify which specific queue is backlogged.

#### Acceptance Criteria

1. THE QueuePanel SHALL render each entry in `queue_depths` as a separate row containing: queue name, depth count, and a status dot (`bg-emerald-400` for 0, `bg-amber-400` for 1–5, `bg-red-400` for 6+).
2. THE QueuePanel SHALL display `active_jobs` and `jobs_in_store` as summary counts above the per-queue rows.
3. THE QueuePanel SHALL sort queue rows by depth descending so that the most backlogged queue appears first.
4. WHEN all queue depths are 0, THE QueuePanel SHALL display all rows with green status dots and SHALL NOT show a "no data" message.

---

### Requirement 12: Dashboard Redesign — Inference Panel with Top Endpoints Table

**User Story:** As an admin, I want the inference panel to show a top-endpoints table with usage counts, so that I can see which endpoints are driving load.

#### Acceptance Criteria

1. THE InferencePanel SHALL display a top-endpoints table with columns: Endpoint, Requests, showing the top 8 entries from `requests_by_endpoint` sorted by request count descending.
2. THE InferencePanel SHALL display `avgLatencySeconds` formatted as `X.XXXs`, `totalRequests` as a formatted integer, and `errorRatePercent` as `X.XX%` in a 3-column stat grid above the table.
3. WHEN `requests_by_endpoint` is empty or null, THE InferencePanel SHALL display "No endpoint data yet" in place of the table.
4. THE InferencePanel SHALL render each endpoint row with a relative usage bar — a horizontal fill bar whose width is proportional to that endpoint's share of total requests — using `bg-cyan-500/20` fill and `bg-zinc-800` track.

---

### Requirement 13: Dashboard Redesign — Cache Panel with Donut Chart

**User Story:** As an admin, I want the cache panel to display a donut chart with hit rate percentage centred inside, so that cache effectiveness is immediately visible.

#### Acceptance Criteria

1. THE CachePanel SHALL render a donut chart (Recharts `PieChart` with `innerRadius` and `outerRadius`) with a cyan segment for hits and a zinc-800 segment for misses.
2. THE CachePanel SHALL display the `cache_hit_rate_percent` value as a percentage centred inside the donut chart using absolute positioning.
3. THE CachePanel SHALL display `cache_hits` and `cache_misses` as labelled counts below or beside the donut.
4. WHEN `cache_hit_rate_percent` is `0`, THE CachePanel SHALL render a fully grey donut (100% miss segment) and display `0.00%` rather than an empty or broken chart.

---

### Requirement 14: Consistent Loading, Error, and Empty States

**User Story:** As an admin, I want every panel and page to handle loading, error, and empty states gracefully, so that the UI never shows broken or misleading content.

#### Acceptance Criteria

1. WHEN any dashboard panel query is loading, THE panel SHALL render skeleton placeholders (`<Skeleton>`) that match the approximate shape of the loaded content.
2. WHEN any dashboard panel query returns an error, THE panel SHALL render an amber-bordered error card showing "Could not reach model-service" and the timestamp of the last successful fetch.
3. WHEN a dashboard panel query succeeds but returns empty data (e.g., zero requests, empty queue map), THE panel SHALL render the panel normally with zero values and SHALL NOT show an error state.
4. THE MonitoringPage SHALL display a dismissible banner WHEN any of its queries are in error state, and SHALL continue to show the last known chart data rather than clearing the charts.
5. WHEN the SettingsPage query is loading, THE SettingsPage SHALL render skeleton rows in place of config values.
6. WHEN the SettingsPage query returns an error, THE SettingsPage SHALL display a red-bordered error card stating the service is unreachable.

---

### Requirement 15: TypeScript Type Accuracy

**User Story:** As a developer, I want the TypeScript types in `types/api.ts` to accurately reflect the actual backend API response shapes, so that field access is type-safe and IDE autocomplete is correct.

#### Acceptance Criteria

1. THE `InferenceMetrics` type SHALL include all fields returned by `/api/v1/metrics/inference`: `total_requests`, `cache_hits`, `cache_misses`, `cache_hit_rate_percent`, `requests_by_endpoint`, `errors`, `batches_processed`, `avg_batch_size`, `total_generation_time_seconds`, and `server_start_time` (typed as `string | null`).
2. THE `GpuMetrics` type SHALL be defined as a standalone exported type (not nested inside `MetricsOverview`) with fields: `available`, `error`, `gpu_util_percent`, `memory_used_percent`, `memory_used_mb`, `memory_total_mb`, `temperature_c`, and `power_watts` — all optional numbers except `available` (boolean) and `error` (string or null).
3. THE `QueuesMetrics` type SHALL be defined as a standalone exported type with fields: `active_jobs` (number), `jobs_in_store` (number), and `queue_depths` (Record<string, number>).
4. THE `MetricsOverview` type SHALL reference `GpuMetrics` for its `gpu` field rather than duplicating the field list inline.
5. THE `StatsResponse` type SHALL NOT include `server_start_time`, as this field does not exist in the `/stats` response.
6. THE `useMetricsGpuQuery` hook SHALL be typed to return `GpuMetrics` rather than `Record<string, unknown>`.
7. THE `useMetricsQueuesQuery` hook SHALL be typed to return `QueuesMetrics` rather than `Record<string, unknown>`.
8. THE `useMetricsInferenceQuery` hook SHALL be typed to return `InferenceMetrics` rather than `Record<string, unknown>`.
