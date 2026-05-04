import { NextRequest, NextResponse } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";

export async function POST(
  req: NextRequest,
  { params }: { params: { competency: string } }
) {
  const body = await req.json();
  try {
    const res = await fetch(`${RAG_URL}/api/v1/ingest/${params.competency}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
