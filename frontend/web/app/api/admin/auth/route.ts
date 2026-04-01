import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "gisul_admin_session";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const token = typeof body?.token === "string" ? body.token : "";
  const expected = process.env.ADMIN_TOKEN || "";

  if (!expected) {
    return new NextResponse("ADMIN_TOKEN is not configured on the server", {
      status: 500,
    });
  }

  if (!token || token !== expected) {
    return new NextResponse("Invalid admin token", { status: 401 });
  }

  const expires = new Date();
  expires.setDate(expires.getDate() + 7);

  cookies().set({
    name: COOKIE_NAME,
    value: "ok",
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires,
  });

  return NextResponse.json({ ok: true });
}

