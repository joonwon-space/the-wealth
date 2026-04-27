import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/manifest.webmanifest",
  "/icon-192.svg",
  "/icon-512.svg",
  "/sw.js",
  "/offline",
];

function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

function buildCsp(nonce: string, isDev: boolean): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    isDev ? "'unsafe-eval'" : "",
    "https://static.cloudflareinsights.com",
  ]
    .filter(Boolean)
    .join(" ");

  const connectSrc = [
    "'self'",
    isDev ? "http://localhost:8000" : "",
    "https://localhost:8000",
    "https://api.joonwon.dev",
    "https://cloudflareinsights.com",
    "https://*.ingest.us.sentry.io",
  ]
    .filter(Boolean)
    .join(" ");

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "img-src 'self' data: blob:",
    "font-src 'self' https://cdn.jsdelivr.net",
    `connect-src ${connectSrc}`,
    "worker-src 'self' blob:",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

function applySecurityHeaders(response: NextResponse, csp: string): NextResponse {
  response.headers.set("content-security-policy", csp);
  return response;
}

const AUTH_COOKIE_NAMES = ["access_token", "refresh_token", "auth_status"] as const;

/**
 * Derive the cookie domain from the request host so middleware-issued cookie
 * deletions match what the backend originally set:
 *   - production (`*.joonwon.dev`) → `.joonwon.dev`
 *   - localhost / single-label hosts → undefined (cookie stays host-only)
 *
 * Reproducing the registrable domain from the host avoids requiring a separate
 * NEXT_PUBLIC_COOKIE_DOMAIN env var.
 */
function deriveCookieDomain(hostname: string): string | undefined {
  if (hostname === "localhost" || /^\d+(\.\d+){3}$/.test(hostname)) return undefined;
  const parts = hostname.split(".");
  if (parts.length < 2) return undefined;
  return "." + parts.slice(-2).join(".");
}

/**
 * Force-clear auth cookies on the response.
 *
 * Used when the client signals a forced re-auth (`/login?reauth=1`) — this is
 * a same-origin Set-Cookie from the frontend's own domain, which Safari mobile
 * honors more reliably than a cross-subdomain Set-Cookie from the API host.
 */
function clearAuthCookies(response: NextResponse, hostname: string): void {
  const cookieDomain = deriveCookieDomain(hostname);
  const secure = process.env.NODE_ENV !== "development";
  for (const name of AUTH_COOKIE_NAMES) {
    const httpOnly = name !== "auth_status";
    response.cookies.set(name, "", {
      maxAge: 0,
      path: "/",
      domain: cookieDomain,
      httpOnly,
      secure,
      sameSite: "lax",
    });
  }
}

export function proxy(request: NextRequest) {
  const { pathname, searchParams, hostname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "?"));
  const isForcedReauth = pathname === "/login" && searchParams.get("reauth") === "1";

  const nonce = generateNonce();
  const csp = buildCsp(nonce, process.env.NODE_ENV === "development");

  // access_token(30분) 또는 refresh_token(7일) 중 하나라도 있으면 로그인 상태로 간주.
  // access_token이 만료돼도 refresh_token이 살아있으면 첫 API 호출 시 인터셉터가 자동 갱신.
  const isLoggedIn = !!(
    request.cookies.get("access_token")?.value ||
    request.cookies.get("refresh_token")?.value
  );

  // 비인증 상태에서 보호된 경로 접근 → 로그인으로
  if (!isPublic && !isLoggedIn) {
    return applySecurityHeaders(
      NextResponse.redirect(new URL("/login", request.url)),
      csp,
    );
  }

  // 강제 재인증 (?reauth=1) — 백엔드 쿠키 삭제가 사파리에서 실패해도
  // 프론트 자기 도메인에서 Set-Cookie 로 다시 한 번 클리어하고
  // /dashboard 자동 리다이렉트 분기를 건너뛴다.
  if (isForcedReauth) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-nonce", nonce);
    requestHeaders.set("content-security-policy", csp);
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    clearAuthCookies(response, hostname);
    return applySecurityHeaders(response, csp);
  }

  // 인증 상태에서 로그인/회원가입 접근 → 대시보드로
  if (isPublic && isLoggedIn) {
    return applySecurityHeaders(
      NextResponse.redirect(new URL("/dashboard", request.url)),
      csp,
    );
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  return applySecurityHeaders(
    NextResponse.next({ request: { headers: requestHeaders } }),
    csp,
  );
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.png|.*\\.jpg|.*\\.ico).*)"],
};
