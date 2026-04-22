"use client";

import { forwardRef, type ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export interface HeroValueProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 섹션 라벨 — 보통 "총 평가금액 · KRW" 등 */
  label: ReactNode;
  /** 큰 숫자 영역에 들어갈 포매팅된 값 (`₩42,180,500`). */
  value: ReactNode;
  /** 오늘 변동 금액 — `formatKRW` 등으로 이미 포매팅된 문자열을 권장. */
  change?: ReactNode;
  /** 오늘 변동 %. 숫자로 주면 sign+색이 자동 적용. */
  changePct?: number | null;
  /**
   * 상승/하락 방향을 수동 지정하고 싶을 때. 미지정 시 `changePct >= 0` 로 유추.
   * 값이 없고 `changePct`도 null이면 중립(muted) 톤.
   */
  up?: boolean;
  /** hero 오른쪽에 붙일 커스텀 슬롯 — sparkline 이나 Progress ring 등. */
  trailing?: ReactNode;
  /** 보조 라인 — 예: "USD/KRW 1,380" */
  footnote?: ReactNode;
}

/**
 * 홈 hero 의 북극성 블록. 토스 스타일의 "총자산 + 오늘 변동" 큰 숫자 카드.
 * 한국 증시 색 규칙을 따르며 색만으로 정보 전달하지 않도록 ▲/▼ 아이콘 병기.
 */
export const HeroValue = forwardRef<HTMLDivElement, HeroValueProps>(
  (
    { label, value, change, changePct, up, trailing, footnote, className, ...props },
    ref,
  ) => {
    const hasPct = changePct != null && Number.isFinite(changePct);
    const direction: "up" | "down" | "flat" = !hasPct
      ? "flat"
      : up !== undefined
        ? up
          ? "up"
          : "down"
        : changePct > 0
          ? "up"
          : changePct < 0
            ? "down"
            : "flat";

    const ArrowIcon =
      direction === "up" ? ArrowUpRight : direction === "down" ? ArrowDownRight : null;
    const toneClass =
      direction === "up"
        ? "text-rise"
        : direction === "down"
          ? "text-fall"
          : "text-muted-foreground";
    const badgeTone =
      direction === "up" ? "rise" : direction === "down" ? "fall" : "neutral";

    return (
      <div
        ref={ref}
        className={cn("flex items-start justify-between gap-4", className)}
        {...props}
      >
        <div className="flex-1 min-w-0">
          <p className="text-section-header mb-2">{label}</p>
          <p className="text-asset-total leading-none">{value}</p>
          {(change != null || hasPct) && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm font-medium">
              {ArrowIcon && <ArrowIcon className={cn("size-4 shrink-0", toneClass)} />}
              {change != null && (
                <span className={cn("tabular-nums", toneClass)}>{change}</span>
              )}
              {hasPct && (
                <Badge tone={badgeTone}>
                  {changePct > 0 ? "+" : ""}
                  {changePct.toFixed(2)}%
                </Badge>
              )}
              <span className="text-metric-label">오늘</span>
            </div>
          )}
          {footnote && (
            <p className="mt-1 text-metric-label text-numeric">{footnote}</p>
          )}
        </div>
        {trailing && <div className="shrink-0">{trailing}</div>}
      </div>
    );
  },
);
HeroValue.displayName = "HeroValue";
