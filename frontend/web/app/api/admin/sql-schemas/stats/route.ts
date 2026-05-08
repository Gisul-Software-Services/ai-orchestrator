import { NextResponse } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";

export async function GET() {
  try {
    const res = await fetch(`${RAG_URL}/api/v1/sql-schemas/stats`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "RAG service unreachable" }, { status: 503 });
  }
}
