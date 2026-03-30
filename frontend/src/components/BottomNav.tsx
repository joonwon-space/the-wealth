"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, BookOpen, Home, Settings, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "홈", icon: Home },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/analytics", label: "분석", icon: BarChart3 },
  { href: "/dashboard/journal", label: "일지", icon: BookOpen },
  { href: "/dashboard/settings", label: "설정", icon: Settings },
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
