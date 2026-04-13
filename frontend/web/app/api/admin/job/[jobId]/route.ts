import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { adminJobs } from "@/lib/adminJobStore";
import { makeAdminProxyGetWithParams } from "@/lib/proxyUtils";
import {
  getAdminSessionCookieName,
  verifyAdminSessionToken,
} from "@/lib/adminSession";

const upstreamGET = makeAdminProxyGetWithParams<{ jobId: string }>(
  ({ jobId }) => `/api/v1/job/${encodeURIComponent(jobId)}`
);

export async function GET(req: NextRequest, ctx: { params: { jobId: string } }) {
  const hasSession = await verifyAdminSessionToken(
    cookies().get(getAdminSessionCookieName())?.value
  );
  if (!hasSession) {
    return NextResponse.json({ error: "UNAUTHENTICATED" }, { status: 401 });
  }

  const jobId = ctx.params.jobId;
  const local = adminJobs().get(jobId);
  if (local) {
    return NextResponse.json(local, { status: 200 });
  }
  return upstreamGET(req, ctx);
}

