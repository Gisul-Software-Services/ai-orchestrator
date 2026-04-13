import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  getAdminSessionCookieName,
  verifyAdminSessionToken,
} from "@/lib/adminSession";

function gatewayBase(): string {
  return (process.env.GATEWAY_BASE_URL || "http://backend-api:7000").replace(/\/$/, "");
}

function currentUtcMonth() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export async function GET() {
  const hasSession = await verifyAdminSessionToken(
    cookies().get(getAdminSessionCookieName())?.value
  );
  if (!hasSession) {
    return NextResponse.json({ error: "UNAUTHENTICATED" }, { status: 401 });
  }

  const apiKey = (process.env.ADMIN_API_KEY || "").trim();
  if (!apiKey) {
    return NextResponse.json(
      { error: "ADMIN_API_KEY is not configured on the server" },
      { status: 500 }
    );
  }

  try {
    // Limitation: backend has no list-all-orgs endpoint, so org list is derived
    // from current-period admin usage activity only.
    const period = currentUtcMonth();
    const resp = await fetch(
      `${gatewayBase()}/billing/v1/admin/usage?period=${encodeURIComponent(period)}`,
      {
        method: "GET",
        headers: { "X-Api-Key": apiKey },
        cache: "no-store",
      }
    );

    const contentType = resp.headers.get("content-type") || "application/json";
    const text = await resp.text();
    if (!resp.ok) {
      return new NextResponse(text, {
        status: resp.status,
        headers: { "content-type": contentType },
      });
    }

    const data = JSON.parse(text) as {
      period?: string;
      orgs?: Array<{ _id?: string; total_tokens?: number; call_count?: number }>;
    };
    const orgs = Array.isArray(data.orgs)
      ? data.orgs
          .map((o) => ({
            org_id: String(o?._id ?? ""),
            total_tokens: o?.total_tokens ?? 0,
            call_count: o?.call_count ?? 0,
          }))
          .filter((o) => o.org_id.length > 0)
      : [];

    return NextResponse.json({ period: data.period ?? period, orgs });
  } catch {
    return NextResponse.json(
      { error: "model-service unreachable" },
      { status: 503 }
    );
  }
}

