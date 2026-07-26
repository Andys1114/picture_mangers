import { NextResponse, type NextRequest } from "next/server";

// Edge cookie-presence gate (PRD F8). Does NOT query the DB — the backend
// validates the session; this only avoids flashing protected UI at anonymous
// visitors. /login and /setup stay public; /api and /media are proxied to the
// backend and bypass this gate.
const PUBLIC = ["/login", "/setup"];

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (PUBLIC.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }
  const token = req.cookies.get("gallery_session")?.value;
  if (token) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Skip static assets, the API proxy, the media proxy, and Next internals.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api|media).*)"],
};
