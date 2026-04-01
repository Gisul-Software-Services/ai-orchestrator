import { makeAdminProxyGet } from "@/lib/proxyUtils";

export const GET = makeAdminProxyGet("/billing/v1/admin/usage");

