"use client";

import { useCallback, useRef } from "react";
import { haptic } from "@/lib/haptic";

interface Options {
  onLongPress: () => void;
  delayMs?: number;
  /** Distance in px the pointer can move before the gesture is cancelled. */
  moveTolerance?: number;
}

type PointerHandlers = {
  onPointerDown: (e: React.PointerEvent) => void;
  onPointerUp: (e: React.PointerEvent) => void;
  onPointerMove: (e: React.PointerEvent) => void;
  onPointerCancel: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
};

export function useLongPress({
  onLongPress,
  delayMs = 500,
  moveTolerance = 12,
}: Options): PointerHandlers {
  const timer = useRef<number | null>(null);
  const startPoint = useRef<{ x: number; y: number } | null>(null);

  const clear = useCallback(() => {
    if (timer.current != null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    startPoint.current = null;
  }, []);

  return {
    onPointerDown: (e) => {
      startPoint.current = { x: e.clientX, y: e.clientY };
      timer.current = window.setTimeout(() => {
        haptic.medium();
        onLongPress();
        clear();
      }, delayMs);
    },
    onPointerUp: clear,
    onPointerMove: (e) => {
      const origin = startPoint.current;
      if (!origin) return;
      const dx = Math.abs(e.clientX - origin.x);
      const dy = Math.abs(e.clientY - origin.y);
      if (dx > moveTolerance || dy > moveTolerance) clear();
    },
    onPointerCancel: clear,
    // Suppress the native browser context menu when long-press fires on desktop.
    onContextMenu: (e) => {
      if (timer.current != null) e.preventDefault();
    },
  };
}
