import { makeAdminProxyDeleteWithParams } from "@/lib/proxyUtils";

export const DELETE = makeAdminProxyDeleteWithParams<{
  orgId: string;
  keyHash: string;
}>(
  ({ orgId, keyHash }) =>
    `/billing/v1/orgs/${encodeURIComponent(orgId)}/keys/${encodeURIComponent(keyHash)}`
);

