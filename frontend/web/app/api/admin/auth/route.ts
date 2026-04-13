import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import {
  createAdminSessionToken,
  getAdminSessionCookieName,
  getAdminSessionExpiryDate,
} from "@/lib/adminSession";

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

  const sessionToken = await createAdminSessionToken();

  cookies().set({
    name: getAdminSessionCookieName(),
    value: sessionToken,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires: getAdminSessionExpiryDate(),
  });

  return NextResponse.json({ ok: true });
}

