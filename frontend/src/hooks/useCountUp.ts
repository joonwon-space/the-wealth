"use client";

import { useEffect, useRef, useState } from "react";

interface UseCountUpOptions {
  /** Target value to animate to */
  target: number;
  /** Animation duration in milliseconds (default: 1200) */
  duration?: number;
  /** Delay before starting in milliseconds (default: 0) */
  delay?: number;
  /** Start value (default: 0) */
  start?: number;
  /** Easing function (default: easeOutExpo) */
  easing?: (t: number) => number;
}

/** Ease-out expo: fast start, smooth deceleration */
function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

/**
 * Animates a number from `start` to `target` over `duration` milliseconds.
 * Uses requestAnimationFrame for smooth 60fps animation.
 * Returns the current animated value.
 */
export function useCountUp({
  target,
  duration = 1200,
  delay = 0,
  start = 0,
  easing = easeOutExpo,
}: UseCountUpOptions): number {
  const [current, setCurrent] = useState<number>(start);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const delayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Cancel any previous animation
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
    }
    if (delayTimerRef.current != null) {
      clearTimeout(delayTimerRef.current);
    }

    const startValue = start;
    const diff = target - startValue;

    if (diff === 0) {
      // Use rAF to avoid calling setState synchronously in an effect
      const id = requestAnimationFrame(() => setCurrent(target));
      return () => cancelAnimationFrame(id);
    }

    const runAnimation = () => {
      startTimeRef.current = null;

      const animate = (timestamp: number) => {
        if (startTimeRef.current === null) {
          startTimeRef.current = timestamp;
        }
        const elapsed = timestamp - startTimeRef.current;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easing(progress);
        const value = startValue + diff * easedProgress;
        setCurrent(value);

        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        }
      };

      rafRef.current = requestAnimationFrame(animate);
    };

    if (delay > 0) {
      delayTimerRef.current = setTimeout(runAnimation, delay);
    } else {
      runAnimation();
    }

    return () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
      }
      if (delayTimerRef.current != null) {
        clearTimeout(delayTimerRef.current);
      }
    };
  }, [target, duration, delay, start, easing]);

  return current;
}
