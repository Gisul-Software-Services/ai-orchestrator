import { UsageOrgDetailClient } from "@/components/usage/UsageOrgDetailClient";
import { currentUtcMonth, isValidPeriod } from "@/components/usage/periodUtils";

function firstParam(v: string | string[] | undefined): string {
  if (v == null) return "";
  return Array.isArray(v) ? (v[0] ?? "") : v;
}

export default function UsageOrgDetailPage({
  params,
  searchParams,
}: {
  params: { orgId: string };
  searchParams: { period?: string | string[] };
}) {
  const period = firstParam(searchParams.period);
  const initialPeriod = isValidPeriod(period) ? period : currentUtcMonth();
  return <UsageOrgDetailClient orgId={decodeURIComponent(params.orgId)} initialPeriod={initialPeriod} />;
}

