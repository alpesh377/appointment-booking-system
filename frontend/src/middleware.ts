import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/dashboard", "/provider", "/admin", "/profile"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!PROTECTED.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return NextResponse.next();
  }

  const session = request.cookies.get("session") ?? request.cookies.get("__Host-session");
  if (!session?.value) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/provider/:path*", "/admin/:path*", "/profile/:path*"],
};
