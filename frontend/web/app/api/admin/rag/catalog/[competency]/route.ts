import { NextRequest, NextResponse } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";

export async function GET(
  req: NextRequest,
  { params }: { params: { competency: string } }
) {
  const search = req.nextUrl.searchParams.get("search") ?? "";
  const limit = req.nextUrl.searchParams.get("limit") ?? "50";
  const offset = req.nextUrl.searchParams.get("offset") ?? "0";

  try {
    const res = await fetch(
      `${RAG_URL}/api/v1/catalog/${params.competency}?search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { competency: string } }
) {
  const { entryId } = await req.json();
  try {
    const res = await fetch(
      `${RAG_URL}/api/v1/catalog/${params.competency}/${encodeURIComponent(entryId)}`,
      { method: "DELETE" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
