import { makeAdminProxyGetWithParams } from "@/lib/proxyUtils";

export const GET = makeAdminProxyGetWithParams<{ orgId: string }>(
  ({ orgId }) => `/billing/v1/orgs/${encodeURIComponent(orgId)}/dashboard`
);

