"use client";

import { forwardRef } from "react";
import { BookOpen, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export type InvestMode = "long" | "short";

export interface ModeToggleProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "onChange"> {
  mode: InvestMode;
  onChange: (mode: InvestMode) => void;
  /** `inline` = 홈 hero 바로 밑 큰 세그먼트. `header` = 상단 헤더용 작은 세그먼트. */
  position?: "inline" | "header";
  /** 장기 / 단타 혼합 비율 (기본 70 / 30) — inline 포지션에서만 부제로 노출. */
  ratio?: { long: number; short: number };
}

const MODES: { key: InvestMode; label: string; icon: typeof BookOpen }[] = [
  { key: "long", label: "장기", icon: BookOpen },
  { key: "short", label: "단타", icon: Zap },
];

/**
 * Dual-brain 모드 토글. `position="inline"` 은 홈 hero 아래 큰 세그먼트,
 * `position="header"` 는 상단 바 안에 들어가는 compact 세그먼트.
 */
export const ModeToggle = forwardRef<HTMLDivElement, ModeToggleProps>(
  ({ mode, onChange, position = "inline", ratio, className, ...props }, ref) => {
    const isHeader = position === "header";

    return (
      <div
        ref={ref}
        role="tablist"
        aria-label="투자 모드"
        className={cn(
          "flex rounded-lg bg-muted p-0.5",
          isHeader ? "gap-1 p-0.5" : "gap-1 p-1",
          className,
        )}
        {...props}
      >
        {MODES.map(({ key, label, icon: Icon }) => {
          const active = key === mode;
          const activeBg = key === "long" ? "var(--primary)" : "var(--rise)";
          const pct = ratio ? (key === "long" ? ratio.long : ratio.short) : null;

          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChange(key)}
              className={cn(
                "inline-flex items-center justify-center gap-1.5 rounded-md border-0 font-semibold transition-colors duration-150",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isHeader
                  ? "px-2.5 py-1 text-[11px]"
                  : "flex-1 px-3 py-2 text-sm",
                active ? "text-white shadow-sm" : "text-muted-foreground",
              )}
              style={{
                background: active ? activeBg : "transparent",
              }}
            >
              <Icon className={cn(isHeader ? "size-3" : "size-3.5")} aria-hidden />
              {label}
              {!isHeader && pct != null && active && (
                <span className="ml-0.5 text-[11px] font-medium opacity-75">
                  {pct}%
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  },
);
ModeToggle.displayName = "ModeToggle";
