import type { JobRecord } from "@/types/api";

declare global {
  // eslint-disable-next-line no-var
  var __gisulAdminJobs: Map<string, JobRecord> | undefined;
}

export function adminJobs(): Map<string, JobRecord> {
  if (!globalThis.__gisulAdminJobs) {
    globalThis.__gisulAdminJobs = new Map<string, JobRecord>();
  }
  return globalThis.__gisulAdminJobs;
}

