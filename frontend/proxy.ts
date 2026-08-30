import createMiddleware from "next-intl/middleware";
import { NextResponse, type NextRequest } from "next/server";

import { locales } from "./i18n";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

/**
 * Production CSP with per-request nonces (the documented Next.js pattern).
 *
 * The request-header copy is what makes Next.js stamp its own bootstrap and
 * chunk scripts with the nonce; the response header is what the browser
 * enforces. Development keeps the relaxed CSP from next.config.js because
 * HMR requires 'unsafe-eval'.
 *
 * For locale-prefixed paths we take over from next-intl's middleware and
 * replicate its per-request behavior (setting the X-NEXT-INTL-LOCALE request
 * header it uses for server-side locale resolution). Locale-less paths fall
 * through to next-intl, which redirects and re-enters this middleware with
 * a prefix.
 */
function withCsp(request: NextRequest, locale: string): NextResponse {
  const nonce = btoa(crypto.randomUUID());
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    "connect-src 'self' wss:",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("X-NEXT-INTL-LOCALE", locale);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export default function proxy(request: NextRequest) {
  if (process.env.NODE_ENV !== "production") {
    return intlMiddleware(request);
  }

  const pathname = request.nextUrl.pathname;
  const locale = locales.find((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`));

  if (!locale) {
    return intlMiddleware(request);
  }

  return withCsp(request, locale);
}

export const config = {
  // Match only internationalized pathnames
  // Exclude: api routes, _next static files, images, favicon, and other static files
  matcher: ["/((?!api|_next|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
