"use client";

import { Skeleton } from "@/components/ui/skeleton";

interface ChartSkeletonProps {
  /** Chart height in pixels (default: 280) */
  height?: number;
  /** Show period selector buttons above the chart (default: false) */
  showPeriodSelector?: boolean;
  /** Number of period buttons to show (default: 5) */
  periodCount?: number;
}

/**
 * Skeleton placeholder for chart components.
 * Matches the visual height and shape of Recharts-based charts.
 */
export function ChartSkeleton({
  height = 280,
  showPeriodSelector = false,
  periodCount = 5,
}: ChartSkeletonProps) {
  return (
    <div className="space-y-3">
      {showPeriodSelector && (
        <div className="flex gap-1">
          {Array.from({ length: periodCount }).map((_, i) => (
            <Skeleton key={i} className="h-7 w-10 rounded-md" />
          ))}
        </div>
      )}
      <div className="relative overflow-hidden rounded-lg" style={{ height }}>
        <Skeleton className="absolute inset-0 rounded-lg" />
        {/* Simulated chart bars at different heights */}
        <div className="absolute inset-x-6 bottom-6 flex items-end gap-1 opacity-40">
          {[60, 45, 70, 55, 80, 65, 75, 50, 85, 70, 90, 60].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t-sm bg-primary/20"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton placeholder for the donut chart (AllocationDonut).
 */
export function DonutSkeleton() {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
      {/* Donut placeholder */}
      <div className="relative flex shrink-0 items-center justify-center" style={{ width: 240, height: 240 }}>
        <Skeleton className="h-60 w-60 rounded-full" />
        {/* Inner circle cutout */}
        <div className="absolute h-36 w-36 rounded-full bg-background" />
        <div className="absolute flex flex-col items-center gap-1">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-5 w-24" />
        </div>
      </div>
      {/* Legend placeholder */}
      <div className="flex flex-col gap-2 pt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3" style={{ gridTemplateColumns: "12px 1fr auto auto" }}>
            <Skeleton className="h-3 w-3 rounded-full shrink-0" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-8" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}
