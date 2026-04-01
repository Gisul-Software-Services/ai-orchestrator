import { OrgDetailClient } from "@/components/orgs/OrgDetailClient";

export default function OrgDetailPage({
  params,
}: {
  params: { orgId: string };
}) {
  return <OrgDetailClient orgId={decodeURIComponent(params.orgId)} />;
}

