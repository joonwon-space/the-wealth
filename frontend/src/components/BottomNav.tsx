"use client";

import { useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Home, Radio, Search, Settings, Wallet, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// Mobile tab bar (redesign-spec.md §4): 홈 · 종목 · 포트폴리오 · 스트림 · 내정보.
const navItems = [
  { href: "/dashboard", label: "홈", icon: Home },
  { href: "/dashboard/stocks", label: "종목", icon: Search },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/stream", label: "스트림", icon: Radio },
  { href: "/dashboard/settings", label: "내정보", icon: Settings },
];

interface NavItemProps {
  href: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
}

/**
 * iOS PWA/Safari quirk: when the document has active momentum scroll, the
 * first tap on a fixed element is consumed by the OS to halt the scroll, so
 * the synthesized `click` never fires and Next.js `<Link>` navigation
 * requires a second tap. `touchend` is always delivered though — we track
 * whether the gesture was a real tap (no significant movement) and push the
 * route directly. The `<Link>` `onClick` still runs on desktop / non-iOS.
 */
function NavItem({ href, label, icon: Icon, active }: NavItemProps) {
  const router = useRouter();
  const startY = useRef<number | null>(null);
  const startX = useRef<number | null>(null);
  const movedRef = useRef(false);
  // Timestamp of the last touch-driven navigation. Used to suppress the
  // synthesized click that follows a touch, so the route is pushed exactly
  // once per tap on iOS (where we handle via touchend) AND on Android /
  // desktop (where click still works normally).
  const touchNavigatedAt = useRef(0);

  const onTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
    startY.current = e.touches[0].clientY;
    movedRef.current = false;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    if (startX.current === null || startY.current === null) return;
    const dx = Math.abs(e.touches[0].clientX - startX.current);
    const dy = Math.abs(e.touches[0].clientY - startY.current);
    // ~tap tolerance: accept tiny jitter, reject deliberate drag/scroll.
    if (dx > 8 || dy > 8) movedRef.current = true;
  };

  const onTouchEnd = () => {
    const wasTap = !movedRef.current && startX.current !== null;
    startX.current = null;
    startY.current = null;
    movedRef.current = false;
    if (!wasTap) return;
    touchNavigatedAt.current = Date.now();
    router.push(href);
  };

  const onClick = (e: React.MouseEvent) => {
    // If touchend already pushed within the last 500ms, swallow the
    // synthesized click to avoid a duplicate navigation. Desktop mouse
    // clicks have no preceding touchend so this branch is skipped and
    // <Link> navigates normally.
    if (Date.now() - touchNavigatedAt.current < 500) {
      e.preventDefault();
    }
  };

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onClick={onClick}
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
}

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      // 기본 56px tab bar + safe-area-inset-bottom (iOS 홈 인디케이터 공간).
      className="fixed bottom-0 left-0 right-0 z-40 flex h-[calc(56px+env(safe-area-inset-bottom,0px))] items-start border-t bg-background/92 pt-1.5 backdrop-blur-md md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="하단 내비게이션"
    >
      {navItems.map((item) => (
        <NavItem
          key={item.href}
          href={item.href}
          label={item.label}
          icon={item.icon}
          active={pathname === item.href}
        />
      ))}
    </nav>
  );
}
