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
  refreshing: boolean;
  threshold: number;
}

/**
 * Mobile pull-to-refresh gesture. Only engages when the scroll container is
 * at the top and the user starts a downward drag from that position.
 *
 * Attach the returned `bind` ref to the scroll container (usually the main
 * content area). The state fields drive an indicator rendered by the caller.
 */
export function usePullToRefresh({
  onRefresh,
  threshold = 64,
  maxPull = 96,
  disabled = false,
}: Options): { bind: React.RefObject<HTMLDivElement | null>; state: State } {
  const bind = useRef<HTMLDivElement | null>(null);
  const startY = useRef<number | null>(null);
  const activeRef = useRef(false);
  const [state, setState] = useState<State>({
    pulling: false,
    distance: 0,
    refreshing: false,
    threshold,
  });

  useEffect(() => {
    if (disabled) return;
    const el = bind.current ?? document.documentElement;
    if (!el) return;

    const getScrollTop = () => {
      if (bind.current) return bind.current.scrollTop;
      return window.scrollY || document.documentElement.scrollTop;
    };

    const onStart = (e: TouchEvent) => {
      if (getScrollTop() > 0) return;
      if (state.refreshing) return;
      startY.current = e.touches[0].clientY;
    };

    const onMove = (e: TouchEvent) => {
      if (startY.current == null) return;
      const delta = e.touches[0].clientY - startY.current;
      if (delta <= 0) return;
      if (getScrollTop() > 0) {
        startY.current = null;
        return;
      }
      activeRef.current = true;
      // Rubber-banding: soft-clamp past threshold so the indicator doesn't run away.
      const distance = Math.min(delta * 0.55, maxPull);
      setState((s) => ({ ...s, pulling: true, distance }));
      if (e.cancelable) e.preventDefault();
    };

    const onEnd = async () => {
      if (!activeRef.current) {
        startY.current = null;
        return;
      }
      const triggered = state.distance >= threshold;
      activeRef.current = false;
      startY.current = null;
      if (!triggered) {
        setState((s) => ({ ...s, pulling: false, distance: 0 }));
        return;
      }
      haptic.light();
      setState((s) => ({ ...s, pulling: false, refreshing: true, distance: threshold }));
      try {
        await onRefresh();
      } finally {
        setState((s) => ({ ...s, refreshing: false, distance: 0 }));
      }
    };

    el.addEventListener("touchstart", onStart as EventListener, { passive: true });
    el.addEventListener("touchmove", onMove as EventListener, { passive: false });
    el.addEventListener("touchend", onEnd as EventListener);
    el.addEventListener("touchcancel", onEnd as EventListener);
    return () => {
      el.removeEventListener("touchstart", onStart as EventListener);
      el.removeEventListener("touchmove", onMove as EventListener);
      el.removeEventListener("touchend", onEnd as EventListener);
      el.removeEventListener("touchcancel", onEnd as EventListener);
    };
  }, [disabled, maxPull, onRefresh, state.distance, state.refreshing, threshold]);

  return { bind, state };
}
