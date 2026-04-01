import { UsageOverviewClient } from "@/components/usage/UsageOverviewClient";
import { currentUtcMonth, isValidPeriod } from "@/components/usage/periodUtils";

function firstParam(v: string | string[] | undefined): string {
  if (v == null) return "";
  return Array.isArray(v) ? (v[0] ?? "") : v;
}

export default function UsageOverviewPage({
  searchParams,
}: {
  searchParams: { period?: string | string[] };
}) {
  const period = firstParam(searchParams.period);
  const initialPeriod = isValidPeriod(period) ? period : currentUtcMonth();
  return <UsageOverviewClient initialPeriod={initialPeriod} />;
}
