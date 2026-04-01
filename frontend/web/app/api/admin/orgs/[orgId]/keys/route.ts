import {
  makeAdminProxyGetWithParams,
  makeAdminProxyPostWithParams,
} from "@/lib/proxyUtils";

export const GET = makeAdminProxyGetWithParams<{ orgId: string }>(
  ({ orgId }) => `/billing/v1/orgs/${encodeURIComponent(orgId)}/keys`
);

export const POST = makeAdminProxyPostWithParams<{ orgId: string }>(
  ({ orgId }) => `/billing/v1/orgs/${encodeURIComponent(orgId)}/keys`
);

