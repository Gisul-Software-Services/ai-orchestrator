import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "gisul_admin_session";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/playground",
  "/monitoring",
  "/usage",
  "/orgs",
  "/catalog",
  "/history",
  "/settings",
];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow auth routes and static assets through
  if (
    pathname.startsWith("/api/admin/auth") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/assets") ||
    pathname === "/"
  ) {
    return NextResponse.next();
  }

  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  const hasSession = req.cookies.get(SESSION_COOKIE)?.value === "ok";
  if (!hasSession) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

