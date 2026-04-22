"use client";

import { forwardRef, type ReactNode } from "react";
import {
  AlertCircle,
  BadgeCheck,
  Coins,
  Scale,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge, type BadgeProps } from "@/components/ui/badge";

export type StreamCardKind = "alert" | "fill" | "rebalance" | "dividend" | "routine";

export interface StreamCardProps
  extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  kind: StreamCardKind;
  title: ReactNode;
  sub?: ReactNode;
  /** 상대 시각 또는 절대 시각 — 이미 포매팅된 문자열 권장. */
  ts?: ReactNode;
  /** 배지 좌측에 들어갈 텍스트. 미지정 시 kind에 따라 기본값 사용. */
  badgeLabel?: ReactNode;
  /** kind 별 기본 톤을 오버라이드 하고 싶을 때. */
  tone?: BadgeProps["tone"];
  /** 좌측 컬러 테두리 색상 토큰 — 기본값은 kind 규칙 따름. */
  accent?: string;
  /** 카드 하단 추가 영역 — 액션 버튼, 프로그레스 바 등. */
  children?: ReactNode;
}

interface KindConfig {
  icon: LucideIcon;
  tone: BadgeProps["tone"];
  label: string;
  accent?: string;
}

const KIND_CONFIG: Record<StreamCardKind, KindConfig> = {
  alert: { icon: AlertCircle, tone: "rise", label: "목표가 도달", accent: "var(--rise)" },
  fill: { icon: BadgeCheck, tone: "ok", label: "체결 완료" },
  rebalance: { icon: Scale, tone: "warn", label: "리밸런싱 제안" },
  dividend: { icon: Coins, tone: "primary", label: "배당 예정" },
  routine: { icon: BadgeCheck, tone: "neutral", label: "루틴" },
};

/**
 * Stream 피드 카드. 5가지 종류 (알림/체결/리밸런싱/배당/루틴) 의 기본 외형을 제공.
 * `children` 으로 액션 버튼·프로그레스 바 등 추가 블록을 붙인다.
 */
export const StreamCard = forwardRef<HTMLElement, StreamCardProps>(
  (
    { kind, title, sub, ts, badgeLabel, tone, accent, children, className, ...props },
    ref,
  ) => {
    const config = KIND_CONFIG[kind];
    const Icon = config.icon;
    const effectiveTone = tone ?? config.tone;
    const effectiveAccent = accent ?? config.accent;

    return (
      <article
        ref={ref}
        className={cn(
          "rounded-xl border border-border bg-card px-4 py-3",
          effectiveAccent ? "border-l-[3px]" : null,
          className,
        )}
        style={effectiveAccent ? { borderLeftColor: effectiveAccent } : undefined}
        {...props}
      >
        <header className="mb-1.5 flex items-center gap-2">
          <Badge tone={effectiveTone} solid={kind === "alert"}>
            <Icon aria-hidden className="size-3" />
            {badgeLabel ?? config.label}
          </Badge>
          {ts && (
            <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
              {ts}
            </span>
          )}
        </header>
        <div className="text-sm font-semibold leading-snug text-foreground">
          {title}
        </div>
        {sub && (
          <div className="mt-0.5 text-xs text-muted-foreground tabular-nums">
            {sub}
          </div>
        )}
        {children && <div className="mt-2.5">{children}</div>}
      </article>
    );
  },
);
StreamCard.displayName = "StreamCard";
