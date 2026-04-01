"use client";

import { OrgsTable } from "@/components/orgs/OrgsTable";
import { useOrgsListQuery } from "@/hooks/useOrgs";

export default function OrgsPage() {
  const query = useOrgsListQuery();
  const rows = query.data?.orgs ?? [];

  return (
    <div className="space-y-8">
      <div>
        <div className="text-2xl font-semibold">Orgs & API Keys</div>
        <div className="mt-1 text-sm text-zinc-400">
          Manage organisations and their API access
        </div>
      </div>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-xs text-cyan-100/90">
        Orgs shown are those with API activity. Orgs with no usage history will not appear
        here.
      </div>

      {query.isLoading ? (
        <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4 text-sm text-zinc-500">
          Loading organisations…
        </div>
      ) : query.isError ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {query.error instanceof Error ? query.error.message : "Failed to load orgs"}
        </div>
      ) : (
        <OrgsTable rows={rows} />
      )}
    </div>
  );
}

