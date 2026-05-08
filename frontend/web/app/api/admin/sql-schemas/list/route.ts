import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = searchParams.get("limit") ?? "200";
    const skip = searchParams.get("skip") ?? "0";
    const domain = searchParams.get("domain") ?? "";
    const params = new URLSearchParams({ limit, skip });
    if (domain) params.set("domain", domain);
    const res = await fetch(`${RAG_URL}/api/v1/sql-schemas/list?${params}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "RAG service unreachable" }, { status: 503 });
  }
}
