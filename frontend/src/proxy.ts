import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/manifest.webmanifest",
  "/icon-192.svg",
  "/icon-512.svg",
];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "?"));

  // access_token(30분) 또는 refresh_token(7일) 중 하나라도 있으면 로그인 상태로 간주.
  // access_token이 만료돼도 refresh_token이 살아있으면 첫 API 호출 시 인터셉터가 자동 갱신.
  const isLoggedIn = !!(
    request.cookies.get("access_token")?.value ||
    request.cookies.get("refresh_token")?.value
  );

  // 비인증 상태에서 보호된 경로 접근 → 로그인으로
  if (!isPublic && !isLoggedIn) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 인증 상태에서 로그인/회원가입 접근 → 대시보드로
  if (isPublic && isLoggedIn) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.png|.*\\.jpg|.*\\.ico).*)"],
};
