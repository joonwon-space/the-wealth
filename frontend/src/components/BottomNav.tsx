"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Radio, Search, Settings, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

// Mobile tab bar (redesign-spec.md §4): 홈 · 종목 · 포트폴리오 · 스트림 · 내정보.
const navItems = [
  { href: "/dashboard", label: "홈", icon: Home },
  { href: "/dashboard/stocks", label: "종목", icon: Search },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/stream", label: "스트림", icon: Radio },
  { href: "/dashboard/settings", label: "내정보", icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      // 기본 56px tab bar + safe-area-inset-bottom (iOS 홈 인디케이터 공간).
      className="fixed bottom-0 left-0 right-0 z-40 flex h-[calc(56px+env(safe-area-inset-bottom,0px))] items-start border-t bg-background/92 pt-1.5 backdrop-blur-md md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="하단 내비게이션"
    >
      {navItems.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className="flex min-h-[44px] flex-1 flex-col items-center justify-start gap-0.5 py-1.5"
          >
            <span
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-xl px-3 py-1 transition-all duration-150",
                active ? "scale-105" : "scale-100",
              )}
              style={
                active
                  ? {
                      background:
                        "color-mix(in oklch, var(--primary) 15%, transparent)",
                    }
                  : undefined
              }
            >
              <Icon
                className={cn(
                  "size-5 transition-colors duration-150",
                  active ? "stroke-[2.25]" : "stroke-[1.75]",
                )}
                style={{ color: active ? "var(--primary)" : undefined }}
              />
              <span
                className={cn(
                  "text-[10px] font-medium transition-colors duration-150",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
                style={active ? { color: "var(--primary)" } : undefined}
              >
                {label}
              </span>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
