"use client";

import { useQuery } from "@tanstack/react-query";
import { adminFetchJson } from "@/lib/adminApi";

export type SettingsPayload = {
  source: "settings-endpoint" | "derived";
  data: any;
};

export function useSettingsQuery() {
  return useQuery({
    queryKey: ["admin", "settings"],
    queryFn: () => adminFetchJson<SettingsPayload>("/api/admin/settings"),
    refetchInterval: 30_000,
  });
}

