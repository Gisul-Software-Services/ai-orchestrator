"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ApiKeysList } from "@/components/orgs/ApiKeysList";
import { OrgProfileCard } from "@/components/orgs/OrgProfileCard";
import { useOrgProfileQuery } from "@/hooks/useOrgs";

export function OrgDetailClient({ orgId }: { orgId: string }) {
  const profileQuery = useOrgProfileQuery(orgId);
  const profile = (profileQuery.data ?? null) as Record<string, unknown> | null;
  const orgName = (profile?.name as string | undefined) ?? null;

  const profileMissing =
    profileQuery.isError &&
    profileQuery.error instanceof Error &&
    (profileQuery.error.message.includes("404") ||
      profileQuery.error.message.toLowerCase().includes("not found"));

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-start gap-3">
          <Button asChild variant="outline" className="border-white/10">
            <Link href="/orgs">Back</Link>
          </Button>
          <div>
            <div className="text-2xl font-semibold">{orgId}</div>
            <div className="mt-1 text-sm text-zinc-400">{orgName ?? "—"}</div>
          </div>
        </div>
      </div>

      {profileMissing ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Organisation profile not found in org database — this org has API activity but no
          registered profile
        </div>
      ) : null}

      {!profileMissing ? <OrgProfileCard profile={profile} /> : null}

      <ApiKeysList orgId={orgId} />

      <div className="rounded-xl border border-red-500/30 bg-zinc-950/40 p-4">
        <div className="text-sm font-medium text-red-300">Danger Zone</div>
        <div className="mt-2 text-sm text-zinc-400">
          Additional org management features coming soon
        </div>
      </div>
    </div>
  );
}

