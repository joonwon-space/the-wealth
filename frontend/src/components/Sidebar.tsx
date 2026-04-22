"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, BookOpen, GitCompare, Home, LogOut, Menu, Moon, Radio, Settings, Sun, Wallet, X } from "lucide-react";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "대시보드", icon: Home },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/stream", label: "스트림", icon: Radio },
  { href: "/dashboard/analytics", label: "분석", icon: BarChart3 },
  { href: "/dashboard/compare", label: "비교", icon: GitCompare },
  { href: "/dashboard/journal", label: "투자 일지", icon: BookOpen },
  { href: "/dashboard/settings", label: "설정", icon: Settings },
];

function BrandMark() {
  return (
    <Image
      src="/logo-mark.svg"
      alt="The Wealth"
      width={20}
      height={20}
      priority
    />
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const logout = useAuthStore((s) => s.logout);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const handleLogout = async () => {
    try {
      // Clear HttpOnly cookies on the backend
      const { api } = await import("@/lib/api");
      await api.post("/auth/logout");
    } catch {
      // Ignore errors — redirect to login regardless
    }
    logout();
    router.push("/login");
  };

  return (
    <>
      {/* Logo & brand */}
      <div className="mb-6 px-2 flex items-center gap-2.5">
        <BrandMark />
        <span className="text-sm font-bold tracking-widest uppercase text-foreground">
          THE WEALTH
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-0.5" aria-label="메인 내비게이션">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-150",
                isActive
                  ? "bg-accent text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50 font-normal"
              )}
            >
              {/* Active left indicator bar */}
              {isActive && (
                <span
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r-full"
                  style={{ background: "var(--accent-indigo)" }}
                />
              )}
              <Icon
                className="h-4 w-4 shrink-0"
                style={isActive ? { color: "var(--accent-indigo)" } : undefined}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom user profile + settings */}
      <div className="flex flex-col gap-0.5 border-t border-border/50 pt-3">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors duration-150"
        >
          {mounted && (theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />)}
          {mounted ? (theme === "dark" ? "라이트 모드" : "다크 모드") : "테마"}
        </button>
        <button
          onClick={handleLogout}
          className="flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors duration-150"
        >
          <LogOut className="h-4 w-4" />
          로그아웃
        </button>

        {/* User avatar placeholder */}
        <div className="mt-2 flex items-center gap-2.5 rounded-md px-3 py-2 border-t border-border/50">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
            style={{ background: "var(--accent-indigo)" }}
            aria-label="사용자 아바타"
          >
            W
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate text-foreground">내 계정</p>
          </div>
          <Link
            href="/dashboard/settings"
            onClick={onNavigate}
            className="shrink-0 flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors duration-150"
            aria-label="설정"
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </>
  );
}

const SWIPE_CLOSE_THRESHOLD = 60; // px

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const touchStartX = useRef<number | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const delta = touchStartX.current - e.changedTouches[0].clientX;
    if (delta > SWIPE_CLOSE_THRESHOLD) setMobileOpen(false);
    touchStartX.current = null;
  };

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-50 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg border bg-background shadow-sm md:hidden"
        aria-label="메뉴 열기"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r bg-sidebar px-3 py-4 transition-transform duration-200 md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-3 top-4 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-sidebar-foreground hover:bg-accent/50"
          aria-label="메뉴 닫기"
        >
          <X className="h-5 w-5" />
        </button>
        <SidebarContent onNavigate={() => setMobileOpen(false)} />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden h-screen w-60 flex-col border-r bg-sidebar px-3 py-4 md:flex">
        <SidebarContent />
      </aside>
    </>
  );
}
