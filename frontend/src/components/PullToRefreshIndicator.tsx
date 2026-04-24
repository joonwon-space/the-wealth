"use client";

import { Loader2, RefreshCw } from "lucide-react";

interface Props {
  distance: number;
  threshold: number;
  refreshing: boolean;
}

/**
 * Visual affordance for pull-to-refresh. Renders above the content; parent
 * is responsible for positioning (typically `sticky top-0`).
 */
export function PullToRefreshIndicator({
  distance,
  threshold,
  refreshing,
}: Props) {
  if (!refreshing && distance <= 0) return null;
  const progress = Math.min(1, distance / threshold);
  const armed = progress >= 1;
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed left-0 right-0 top-0 z-30 flex justify-center transition-transform md:hidden"
      style={{
        transform: `translateY(${refreshing ? threshold : distance}px)`,
        opacity: refreshing || distance > 8 ? 1 : 0,
      }}
    >
      <div className="mt-2 flex size-9 items-center justify-center rounded-full border bg-card shadow-sm">
        {refreshing ? (
          <Loader2 className="size-4 animate-spin text-primary" />
        ) : (
          <RefreshCw
            className="size-4 transition-transform"
            style={{
              transform: `rotate(${progress * 180}deg)`,
              color: armed ? "var(--primary)" : "var(--muted-foreground)",
            }}
          />
        )}
      </div>
    </div>
  );
}
