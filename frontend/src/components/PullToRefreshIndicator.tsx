"use client";

import { Loader2, RefreshCw } from "lucide-react";

interface Props {
  distance: number;
  threshold: number;
  armed: boolean;
  refreshing: boolean;
}

/**
 * Visual affordance for pull-to-refresh.
 *
 * Only rendered visible when the gesture is `armed` (past threshold, release
 * will refresh) or `refreshing`. During the pre-threshold "tentative pull"
 * phase we show nothing — this avoids the indicator flashing in and out on
 * small, accidental, or hesitant pulls.
 *
 * The circle is positioned by the parent (fixed at viewport top); we apply
 * `translateY` so it rides with the finger once armed.
 */
export function PullToRefreshIndicator({
  distance,
  threshold,
  armed,
  refreshing,
}: Props) {
  const visible = refreshing || armed;
  // Follow the finger while armed; pin at the threshold position during the
  // actual refresh spinner so it doesn't snap around.
  const translateY = refreshing ? threshold : distance;

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed left-0 right-0 top-0 z-30 flex justify-center md:hidden"
      style={{
        transform: `translateY(${translateY}px)`,
        opacity: visible ? 1 : 0,
        transition: "opacity 150ms ease-out",
      }}
    >
      <div
        className="mt-2 flex size-11 items-center justify-center rounded-full shadow-md"
        style={{
          backgroundColor: "var(--primary)",
          border: "1px solid var(--primary)",
        }}
      >
        {refreshing ? (
          <Loader2
            className="animate-spin"
            style={{
              width: 18,
              height: 18,
              color: "var(--primary-foreground)",
            }}
          />
        ) : (
          <RefreshCw
            style={{
              width: 18,
              height: 18,
              color: "var(--primary-foreground)",
            }}
          />
        )}
      </div>
    </div>
  );
}
