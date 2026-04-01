import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { adminJobs } from "@/lib/adminJobStore";

const SESSION_COOKIE = "gisul_admin_session";

function gatewayBase(): string {
  return (process.env.GATEWAY_BASE_URL || "http://backend-api:7000").replace(/\/$/, "");
}

export async function POST(req: NextRequest) {
  const hasSession = cookies().get(SESSION_COOKIE)?.value === "ok";
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

  const jobId = `admin-${crypto.randomUUID()}`;
  adminJobs().set(jobId, { status: "pending", result: null, error: null });

  let body: unknown = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  // Run in the background; the browser will poll /api/admin/job/[jobId]
  (async () => {
    adminJobs().set(jobId, { status: "processing", result: null, error: null });
    try {
      const resp = await fetch(`${gatewayBase()}/api/v1/enrich-dsa`, {
        method: "POST",
        headers: {
          "X-Api-Key": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      });
      const text = await resp.text();
      if (!resp.ok) {
        adminJobs().set(jobId, {
          status: "failed",
          result: null,
          error: text.slice(0, 500) || `Upstream error ${resp.status}`,
        });
        return;
      }
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        // keep text
      }
      adminJobs().set(jobId, { status: "complete", result: parsed, error: null });
    } catch (e) {
      adminJobs().set(jobId, {
        status: "failed",
        result: null,
        error: (e as Error).message || "model-service unreachable",
      });
    }
  })();

  return NextResponse.json({ job_id: jobId, status: "pending" });
}
