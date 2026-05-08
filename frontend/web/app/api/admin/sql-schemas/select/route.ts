import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const params = new URLSearchParams();
    ["difficulty", "sql_category", "domain", "limit", "max_tables", "min_columns"].forEach(k => {
      const v = searchParams.get(k);
      if (v) params.set(k, v);
    });
    const res = await fetch(`${RAG_URL}/api/v1/sql-schemas/select?${params}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "RAG service unreachable" }, { status: 503 });
  }
}
