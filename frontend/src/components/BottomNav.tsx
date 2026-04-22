"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Radio, Settings, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

// Mobile tab bar (redesign-spec.md §4). 5개 항목이 spec 권장이나 "종목" 탭은
// 독립된 /dashboard/stocks 랜딩이 Step 6 에 완성될 때 추가한다.
const navItems = [
  { href: "/dashboard", label: "홈", icon: Home },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/stream", label: "스트림", icon: Radio },
  { href: "/dashboard/settings", label: "내정보", icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex h-16 items-center border-t bg-background/95 backdrop-blur-sm md:hidden"
      aria-label="하단 내비게이션"
    >
      {navItems.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className="flex flex-1 flex-col items-center justify-center gap-0.5 py-2"
          >
            <span
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-xl px-3 py-1 transition-all duration-150",
                active
                  ? "scale-105"
                  : "scale-100"
              )}
              style={
                active
                  ? {
                      background: "color-mix(in oklch, var(--accent-indigo) 15%, transparent)",
                    }
                  : undefined
              }
            >
              <Icon
                className={cn("h-5 w-5 transition-colors duration-150", active ? "stroke-[2.5]" : "stroke-[1.5]")}
                style={{ color: active ? "var(--accent-indigo)" : undefined }}
              />
              <span
                className={cn(
                  "text-[10px] font-medium transition-colors duration-150",
                  active ? "text-foreground" : "text-muted-foreground"
                )}
                style={active ? { color: "var(--accent-indigo)" } : undefined}
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
