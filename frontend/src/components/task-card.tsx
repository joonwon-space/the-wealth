"use client";

import { forwardRef, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TaskCardProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "title"> {
  icon: ReactNode;
  title: ReactNode;
  sub?: ReactNode;
  /** 아이콘 타일의 강조색 — `var(--primary)` 등. 기본은 `var(--primary)`. */
  accent?: string;
  /** 오른쪽 chevron 숨기기 */
  hideArrow?: boolean;
}

/**
 * "오늘 할 것" 피드의 개별 카드. lucide 아이콘 + 제목 + 부제 + 우측 chevron.
 * 클릭 가능한 행이므로 `<button>` 으로 렌더링.
 */
export const TaskCard = forwardRef<HTMLButtonElement, TaskCardProps>(
  (
    {
      icon,
      title,
      sub,
      accent = "var(--primary)",
      hideArrow = false,
      className,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          "flex w-full items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-left transition-colors",
          "hover:bg-muted/40 active:scale-[0.995]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:opacity-50 disabled:pointer-events-none",
          className,
        )}
        {...props}
      >
        <span
          aria-hidden
          className="flex size-8 shrink-0 items-center justify-center rounded-md [&_svg]:size-4"
          style={{
            background: `color-mix(in oklab, ${accent} 15%, transparent)`,
            color: accent,
          }}
        >
          {icon}
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-semibold leading-tight text-foreground">
            {title}
          </span>
          {sub && (
            <span className="mt-0.5 truncate text-xs text-muted-foreground">
              {sub}
            </span>
          )}
        </span>
        {!hideArrow && (
          <ChevronRight aria-hidden className="size-4 shrink-0 text-muted-foreground" />
        )}
      </button>
    );
  },
);
TaskCard.displayName = "TaskCard";
