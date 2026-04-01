import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "gisul_admin_session";

function gatewayBase(): string {
  return (process.env.GATEWAY_BASE_URL || "http://backend-api:7000").replace(/\/$/, "");
}

async function upstreamGet(path: string, apiKey: string) {
  const resp = await fetch(`${gatewayBase()}${path}`, {
    method: "GET",
    headers: { "X-Api-Key": apiKey },
    cache: "no-store",
  });
  const text = await resp.text();
  let json: any = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { status: resp.status, json, text };
}

export async function GET() {
  if (cookies().get(SESSION_COOKIE)?.value !== "ok") {
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
    const settingsRes = await upstreamGet("/api/v1/settings", apiKey);
    if (settingsRes.status >= 200 && settingsRes.status < 300) {
      return NextResponse.json({ source: "settings-endpoint", data: settingsRes.json });
    }

    // Backend currently has no dedicated /api/v1/settings endpoint in this stack.
    // Fallback: derive read-only settings view from /health + /stats snapshots.
    const [healthRes, statsRes, overviewRes] = await Promise.all([
      upstreamGet("/health", apiKey),
      upstreamGet("/stats", apiKey),
      upstreamGet("/api/v1/metrics/overview", apiKey),
    ]);

    return NextResponse.json({
      source: "derived",
      data: {
        health: healthRes.json,
        stats: statsRes.json,
        overview: overviewRes.json,
      },
    });
  } catch {
    return NextResponse.json({ error: "model-service unreachable" }, { status: 503 });
  }
}

