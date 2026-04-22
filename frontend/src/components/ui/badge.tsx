"use client";

import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold leading-tight whitespace-nowrap tabular-nums",
  {
    variants: {
      tone: {
        neutral: "bg-muted text-foreground",
        rise: "bg-rise/15 text-rise",
        fall: "bg-fall/15 text-fall",
        warn: "bg-accent-amber/15 text-accent-amber",
        ok: "bg-chart-8/15 text-chart-8",
        primary: "bg-primary/15 text-primary",
      },
      solid: {
        true: "",
        false: "",
      },
    },
    compoundVariants: [
      { tone: "neutral", solid: true, class: "bg-foreground text-background" },
      { tone: "rise", solid: true, class: "bg-rise text-white" },
      { tone: "fall", solid: true, class: "bg-fall text-white" },
      { tone: "warn", solid: true, class: "bg-accent-amber text-white" },
      { tone: "ok", solid: true, class: "bg-chart-8 text-white" },
      { tone: "primary", solid: true, class: "bg-primary text-primary-foreground" },
    ],
    defaultVariants: {
      tone: "neutral",
      solid: false,
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, tone, solid, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ tone, solid }), className)} {...props} />
  ),
);
Badge.displayName = "Badge";
