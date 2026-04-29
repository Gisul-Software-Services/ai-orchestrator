"use client";

import { OrgsTable } from "@/components/orgs/OrgsTable";
import { useOrgsListQuery } from "@/hooks/useOrgs";
import { Skeleton } from "@/components/ui/skeleton";
import { Users } from "lucide-react";

export default function OrgsPage() {
  const query = useOrgsListQuery();
  const rows = query.data?.orgs ?? [];

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-bold text-zinc-50">Orgs & API Keys</div>
          <div className="mt-1 text-sm text-zinc-500">
            Manage organisations and their API access
          </div>
        </div>
        {query.data && (
          <div className="flex items-center gap-2 rounded-full border border-zinc-800/60 bg-zinc-900/60 px-3 py-1.5">
            <Users className="h-3.5 w-3.5 text-console-accent" />
            <span className="text-xs font-medium text-zinc-300">
              {rows.length} org{rows.length !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-xs text-cyan-300/80">
        Orgs shown are those with API activity in the current billing period. Orgs with no usage will not appear here.
      </div>

      {query.isLoading ? (
        <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 space-y-2">
          <Skeleton className="h-9 w-64" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          {query.error instanceof Error ? query.error.message : "Failed to load orgs"}
        </div>
      ) : (
        <OrgsTable rows={rows} />
      )}
    </div>
  );
}
