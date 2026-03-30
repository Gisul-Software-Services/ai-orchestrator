import { OrgUsageClient } from "@/components/billing/OrgUsageClient";

function firstParam(v: string | string[] | undefined): string {
  if (v == null) return "";
  return Array.isArray(v) ? (v[0] ?? "") : v;
}

export default function OrgUsagePage({
  searchParams,
}: {
  searchParams: { org?: string | string[]; period?: string | string[] };
}) {
  const initialOrgId = firstParam(searchParams.org);
  const initialPeriod = firstParam(searchParams.period);

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
          Organization usage
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed text-zinc-400">
          Browse all organizations for a billing period, then open analytics for one org
          (tokens, routes, latency, logs). Usage is keyed by{" "}
          <code className="text-zinc-500">X-Org-Id</code> and stored in the billing database.
          Deep-link:{" "}
          <code className="text-zinc-500">/usage?org=YOUR_ORG_ID&amp;period=YYYY-MM</code>.
        </p>
      </header>
      <OrgUsageClient initialOrgId={initialOrgId} initialPeriod={initialPeriod} />
    </div>
  );
}
