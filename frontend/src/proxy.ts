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

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self' http://localhost:8000 https://localhost:8000 https://api.joonwon.dev https://cloudflareinsights.com https://*.ingest.us.sentry.io",
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

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "?"));

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
