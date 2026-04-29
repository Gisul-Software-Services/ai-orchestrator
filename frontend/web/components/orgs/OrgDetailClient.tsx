"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ApiKeysList } from "@/components/orgs/ApiKeysList";
import { OrgProfileCard } from "@/components/orgs/OrgProfileCard";
import { useOrgProfileQuery } from "@/hooks/useOrgs";
import { Skeleton } from "@/components/ui/skeleton";
import { Building2, ExternalLink } from "lucide-react";

function extractName(profile: Record<string, unknown> | null): string | null {
  if (!profile) return null;
  const inner = (profile.org as Record<string, unknown> | undefined) ?? profile;
  return (
    (inner.name as string | undefined) ??
    (inner.orgName as string | undefined) ??
    null
  );
}

export function OrgDetailClient({ orgId }: { orgId: string }) {
  const profileQuery = useOrgProfileQuery(orgId);
  const profile = (profileQuery.data ?? null) as Record<string, unknown> | null;
  const orgName = extractName(profile);

  const profileMissing =
    profileQuery.isError &&
    profileQuery.error instanceof Error &&
    (profileQuery.error.message.includes("404") ||
      profileQuery.error.message.toLowerCase().includes("not found"));

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <Button asChild variant="outline" className="mt-1 h-8 border-zinc-700/60 px-3 text-xs">
            <Link href="/orgs">← Back</Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800/60 bg-zinc-900">
                <Building2 className="h-4 w-4 text-console-accent" strokeWidth={1.5} />
              </div>
              <div>
                <div className="text-xl font-bold text-zinc-50">{orgId}</div>
                {profileQuery.isLoading ? (
                  <Skeleton className="mt-1 h-3 w-32" />
                ) : orgName ? (
                  <div className="text-sm text-zinc-400">{orgName}</div>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/usage/${encodeURIComponent(orgId)}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700/60 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-cyan-500/40 hover:text-console-accent"
          >
            <ExternalLink className="h-3 w-3" />
            View Usage
          </Link>
        </div>
      </div>

      {/* Profile missing warning */}
      {profileMissing && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          Organisation profile not found in org database — this org has API activity but no registered profile.
        </div>
      )}

      {/* Profile card */}
      {!profileMissing && (
        profileQuery.isLoading ? (
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5">
            <Skeleton className="h-4 w-40 mb-4" />
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[1,2,3,4].map(i => <Skeleton key={i} className="h-16 rounded-lg" />)}
            </div>
          </div>
        ) : (
          <OrgProfileCard profile={profile} />
        )
      )}

      {/* API Keys */}
      <ApiKeysList orgId={orgId} />
    </div>
  );
}
