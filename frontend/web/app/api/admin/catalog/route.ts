import { makeAdminProxyGet, makeAdminProxyPost } from "@/lib/proxyUtils";

export const GET = makeAdminProxyGet("/api/v1/catalog");
export const POST = makeAdminProxyPost("/api/v1/catalog");

