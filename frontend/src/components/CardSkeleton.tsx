"use client";

import { Skeleton } from "@/components/ui/skeleton";

interface CardSkeletonProps {
  /** Show a top accent bar (default: true) */
  showAccentBar?: boolean;
  /** Show icon placeholder in top right (default: true) */
  showIcon?: boolean;
  /** Show a second value line below the main value (default: false) */
  showSubValue?: boolean;
}

/**
 * Skeleton placeholder for MetricCard layout.
 * Matches the visual shape of cards used in the dashboard summary.
 */
export function CardSkeleton({
  showAccentBar = true,
  showIcon = true,
  showSubValue = false,
}: CardSkeletonProps) {
  return (
    <div className="relative overflow-hidden rounded-xl border bg-card p-4">
      {showAccentBar && <Skeleton className="absolute top-0 left-0 right-0 h-0.5 rounded-none" />}
      <div className="flex items-center justify-between mb-3">
        <Skeleton className="h-3 w-20" />
        {showIcon && <Skeleton className="h-7 w-7 rounded-full" />}
      </div>
      <Skeleton className="h-7 w-32 mb-1" />
      {showSubValue && <Skeleton className="h-3 w-16" />}
    </div>
  );
}

/**
 * Skeleton placeholder for the total asset large card at the top of the dashboard.
 */
export function LargeCardSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-xl border bg-card p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-10 w-48" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        {/* Sparkline placeholder */}
        <Skeleton className="h-16 w-32 shrink-0 rounded-lg ml-4" />
      </div>
    </div>
  );
}
