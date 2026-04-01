import { makeAdminProxyGet } from "@/lib/proxyUtils";

export const GET = makeAdminProxyGet("/api/v1/metrics/gpu");

