"use client";

import { useEffect, useRef, useState } from "react";
import { haptic } from "@/lib/haptic";

interface Options {
  onRefresh: () => Promise<void> | void;
  /** Pull distance (px) required to trigger refresh. */
  threshold?: number;
  /** Maximum pull distance the indicator will render at. */
  maxPull?: number;
  /** Disable the gesture (e.g. on desktop). */
  disabled?: boolean;
}

interface State {
  pulling: boolean;
  distance: number;
  armed: boolean;
  refreshing: boolean;
  threshold: number;
}

// Gate the gesture so it does not hijack normal scrolling.
// Deliberately conservative so a shaky finger or accidental bounce does not
// fire a refresh.
//
// Tuned via: raw_finger_travel_to_arm ≈ (threshold / DAMPING) + ACTIVATION_PX
//   default: (80 / 0.45) + 24 = 202px — deliberate, iOS-native-ish feel.
const HORIZONTAL_TOLERANCE = 1.2;
const ACTIVATION_THRESHOLD_PX = 24;
const DAMPING = 0.45;

/**
 * Mobile pull-to-refresh gesture. Attaches touch listeners to the document
 * root but activates only when the designated scroll container is at its
 * top, and only when the gesture is clearly vertical.
 *
 * UX contract:
 *   - user sees the indicator only after pulling past ACTIVATION_THRESHOLD_PX
 *   - indicator "arms" (primary color, scaled) the first time `distance`
 *     crosses `threshold` — fires a light haptic so the user feels the click
 *   - dis-arms (and haptic again) if the user pulls back above threshold
 *   - refresh fires on touchend iff armed at release
 */
export function usePullToRefresh({
  onRefresh,
  threshold = 80,
  maxPull = 120,
  disabled = false,
}: Options): { state: State } {
  const [state, setState] = useState<State>({
    pulling: false,
    distance: 0,
    armed: false,
    refreshing: false,
    threshold,
  });
  // Mirror state into refs so the touchmove handler can read the latest value
  // without retriggering the effect (which would re-bind listeners on every
  // frame and race with the in-flight gesture).
  const distanceRef = useRef(0);
  const armedRef = useRef(false);
  const refreshingRef = useRef(false);
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;

  useEffect(() => {
    if (disabled) return;
    if (typeof window === "undefined") return;

    // Document/body is the scroll container (see dashboard layout). This keeps
    // iOS status-bar-tap-to-top working natively.
    const getScrollTop = (): number =>
      window.scrollY ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0;

    let startX: number | null = null;
    let startY: number | null = null;
    let active = false;

    const reset = () => {
      startX = null;
      startY = null;
      active = false;
    };

    const commitState = (next: Partial<State>) => {
      if (next.distance !== undefined) distanceRef.current = next.distance;
      if (next.armed !== undefined) armedRef.current = next.armed;
      if (next.refreshing !== undefined) refreshingRef.current = next.refreshing;
      setState((prev) => ({ ...prev, ...next }));
    };

    const onStart = (e: TouchEvent) => {
      if (refreshingRef.current) return;
      if (getScrollTop() > 0) return;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      active = false;
    };

    const onMove = (e: TouchEvent) => {
      if (startX === null || startY === null) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;

      // If gesture becomes horizontal, abort. This prevents the refresh
      // indicator from appearing when the user swipes sideways (carousels,
      // the iOS back-swipe gesture, or accidental diagonal motion).
      if (!active && Math.abs(dx) > Math.abs(dy) * HORIZONTAL_TOLERANCE) {
        reset();
        return;
      }

      // Upward or tiny vertical movement — let native scroll handle it.
      if (dy < ACTIVATION_THRESHOLD_PX) return;

      // Scroller may have been scrolled since touchstart (e.g. iOS momentum).
      if (getScrollTop() > 0) {
        reset();
        return;
      }

      active = true;
      // Rubber-banding: soft-clamp past threshold so the indicator does not
      // run away while still letting the user feel they've "overshot".
      const next = Math.min((dy - ACTIVATION_THRESHOLD_PX) * DAMPING, maxPull);
      const nextArmed = next >= threshold;

      // Haptic click at arming / disarming transitions so the user gets a
      // tactile confirmation of "now I'm past the trigger point" before
      // they commit by releasing.
      if (nextArmed && !armedRef.current) {
        haptic.medium();
      } else if (!nextArmed && armedRef.current) {
        haptic.light();
      }

      commitState({ pulling: true, distance: next, armed: nextArmed });
      if (e.cancelable) e.preventDefault();
    };

    const finish = async () => {
      if (!active) {
        reset();
        return;
      }
      const triggered = armedRef.current;
      reset();
      if (!triggered) {
        commitState({ pulling: false, distance: 0, armed: false });
        return;
      }
      commitState({
        pulling: false,
        refreshing: true,
        distance: threshold,
        armed: false,
      });
      try {
        await onRefreshRef.current();
      } finally {
        commitState({ refreshing: false, distance: 0 });
      }
    };

    document.addEventListener("touchstart", onStart, { passive: true });
    // passive:false only because we need preventDefault while pulling; when
    // we abort early we do NOT call preventDefault, so native scroll is
    // preserved.
    document.addEventListener("touchmove", onMove, { passive: false });
    document.addEventListener("touchend", finish);
    document.addEventListener("touchcancel", finish);
    return () => {
      document.removeEventListener("touchstart", onStart);
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", finish);
      document.removeEventListener("touchcancel", finish);
    };
  }, [disabled, maxPull, threshold]);

  return { state };
}
