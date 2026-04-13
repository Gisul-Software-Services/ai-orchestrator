import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import {
  getAdminSessionCookieName,
  verifyAdminSessionToken,
} from "@/lib/adminSession";

function gatewayBase(): string {
  // In docker-compose, the gateway container is backend-api:7000
  return (process.env.GATEWAY_BASE_URL || "http://backend-api:7000").replace(/\/$/, "");
}

async function requireAdminSession(): Promise<boolean> {
  return verifyAdminSessionToken(
    cookies().get(getAdminSessionCookieName())?.value
  );
}

async function _proxyJson({
  req,
  method,
  upstreamPath,
}: {
  req?: NextRequest;
  method: "GET" | "POST" | "PUT" | "DELETE";
  upstreamPath: string;
}) {
  if (!(await requireAdminSession())) {
    return NextResponse.json({ error: "UNAUTHENTICATED" }, { status: 401 });
  }

  const apiKey = (process.env.ADMIN_API_KEY || "").trim();
  if (!apiKey) {
    return NextResponse.json(
      { error: "ADMIN_API_KEY is not configured on the server" },
      { status: 500 }
    );
  }

  const path = upstreamPath.startsWith("/") ? upstreamPath : `/${upstreamPath}`;
  const search = req?.nextUrl?.search ?? "";
  const url = `${gatewayBase()}${path}${search}`;

  let body: string | undefined;
  if (method === "POST" || method === "PUT") {
    try {
      body = JSON.stringify(await req?.json());
    } catch {
      body = JSON.stringify({});
    }
  }

  try {
    const resp = await fetch(url, {
      method,
      headers: {
        "X-Api-Key": apiKey,
        ...(method === "POST" || method === "PUT"
          ? { "Content-Type": "application/json" }
          : {}),
      },
      body,
      cache: "no-store",
    });

    const contentType = resp.headers.get("content-type") || "application/json";
    const text = await resp.text();
    return new NextResponse(text, {
      status: resp.status,
      headers: { "content-type": contentType },
    });
  } catch {
    return NextResponse.json(
      { error: "model-service unreachable" },
      { status: 503 }
    );
  }
}

export function makeAdminProxyGet(upstreamPath: string) {
  return async function GET(req: NextRequest) {
    return _proxyJson({ req, method: "GET", upstreamPath });
  };
}

export function makeAdminProxyPost(upstreamPath: string) {
  return async function POST(req: NextRequest) {
    return _proxyJson({ req, method: "POST", upstreamPath });
  };
}

export function makeAdminProxyPut(upstreamPath: string) {
  return async function PUT(req: NextRequest) {
    return _proxyJson({ req, method: "PUT", upstreamPath });
  };
}

export function makeAdminProxyDelete(upstreamPath: string) {
  return async function DELETE(req: NextRequest) {
    return _proxyJson({ req, method: "DELETE", upstreamPath });
  };
}

export function makeAdminProxyGetWithParams<Params extends Record<string, string>>(
  buildPath: (params: Params) => string
) {
  return async function GET(req: NextRequest, ctx: { params: Params }) {
    return _proxyJson({ req, method: "GET", upstreamPath: buildPath(ctx.params) });
  };
}

export function makeAdminProxyPostWithParams<Params extends Record<string, string>>(
  buildPath: (params: Params) => string
) {
  return async function POST(req: NextRequest, ctx: { params: Params }) {
    return _proxyJson({ req, method: "POST", upstreamPath: buildPath(ctx.params) });
  };
}

export function makeAdminProxyPutWithParams<Params extends Record<string, string>>(
  buildPath: (params: Params) => string
) {
  return async function PUT(req: NextRequest, ctx: { params: Params }) {
    return _proxyJson({ req, method: "PUT", upstreamPath: buildPath(ctx.params) });
  };
}

export function makeAdminProxyDeleteWithParams<
  Params extends Record<string, string>,
>(buildPath: (params: Params) => string) {
  return async function DELETE(req: NextRequest, ctx: { params: Params }) {
    return _proxyJson({
      req,
      method: "DELETE",
      upstreamPath: buildPath(ctx.params),
    });
  };
}

