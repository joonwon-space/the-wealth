"use client";

import { Loader2, RefreshCw } from "lucide-react";

interface Props {
  distance: number;
  threshold: number;
  armed: boolean;
  refreshing: boolean;
}

/**
 * Visual affordance for pull-to-refresh. Renders above the content; parent
 * is responsible for positioning (typically `sticky top-0`).
 *
 * Three visual states:
 *   1. pulling (distance < threshold): muted arrow rotating toward 180°
 *   2. armed  (distance >= threshold): primary color, slight pop, arrow locked
 *   3. refreshing: spinner, pinned at threshold distance
 */
export function PullToRefreshIndicator({
  distance,
  threshold,
  armed,
  refreshing,
}: Props) {
  if (!refreshing && distance <= 0) return null;
  const progress = Math.min(1, distance / threshold);
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed left-0 right-0 top-0 z-30 flex justify-center md:hidden"
      style={{
        transform: `translateY(${refreshing ? threshold : distance}px)`,
        opacity: refreshing || distance > 12 ? 1 : 0,
        transition: refreshing
          ? "transform 200ms ease-out"
          : "transform 80ms linear",
      }}
    >
      <div
        className="mt-2 flex items-center justify-center rounded-full border shadow-md transition-all duration-150"
        style={{
          // Grow slightly at arm to signal commit, and swap colors from
          // neutral card → primary-tinted.
          width: armed ? 44 : 36,
          height: armed ? 44 : 36,
          backgroundColor: armed ? "var(--primary)" : "var(--card)",
          borderColor: armed
            ? "var(--primary)"
            : "color-mix(in oklch, var(--border) 80%, transparent)",
        }}
      >
        {refreshing ? (
          <Loader2
            className="animate-spin"
            style={{ width: 18, height: 18, color: "var(--primary)" }}
          />
        ) : (
          <RefreshCw
            className="transition-transform duration-150"
            style={{
              width: armed ? 18 : 16,
              height: armed ? 18 : 16,
              transform: `rotate(${progress * 180}deg)`,
              color: armed
                ? "var(--primary-foreground)"
                : "var(--muted-foreground)",
            }}
          />
        )}
      </div>
    </div>
  );
}
