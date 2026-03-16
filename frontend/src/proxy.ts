import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "?"));

  const token = request.cookies.get("access_token")?.value;

  // 비인증 상태에서 보호된 경로 접근 → 로그인으로
  if (!isPublic && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 인증 상태에서 로그인/회원가입 접근 → 대시보드로
  if (isPublic && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|public).*)"],
};
