import {
  makeAdminProxyDeleteWithParams,
  makeAdminProxyGetWithParams,
  makeAdminProxyPutWithParams,
} from "@/lib/proxyUtils";

export const GET = makeAdminProxyGetWithParams<{ catalogId: string }>(
  ({ catalogId }) => `/api/v1/catalog/${encodeURIComponent(catalogId)}`
);

export const PUT = makeAdminProxyPutWithParams<{ catalogId: string }>(
  ({ catalogId }) => `/api/v1/catalog/${encodeURIComponent(catalogId)}`
);

export const DELETE = makeAdminProxyDeleteWithParams<{ catalogId: string }>(
  ({ catalogId }) => `/api/v1/catalog/${encodeURIComponent(catalogId)}`
);

