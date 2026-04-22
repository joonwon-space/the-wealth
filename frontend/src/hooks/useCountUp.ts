"use client";

import { useEffect, useRef, useState } from "react";

interface UseCountUpOptions {
  /** Target value to animate to */
  target: number;
  /** Animation duration in milliseconds (default: 700) */
  duration?: number;
  /** Delay before starting in milliseconds (default: 0) */
  delay?: number;
  /** Start value (default: 0) */
  start?: number;
  /** Easing function (default: linear — all digits climb at the same rate) */
  easing?: (t: number) => number;
}

/**
 * Linear easing.
 *
 * 비선형 이징(예: easeOutExpo)을 쓰면 보간값이 초반에 target 근처로 급히
 * 도달해서 높은 자리수는 일찍 확정되고 낮은 자리수만 계속 바뀌는
 * "위에서부터 순서대로 올라가는" 착시가 생긴다. linear 를 쓰면
 * 모든 자리가 균일한 속도로 함께 증가한다.
 */
function linear(t: number): number {
  return t;
}

/**
 * Animates a number toward `target` over `duration` milliseconds.
 *
 * - 첫 렌더: `start` (기본 0) → `target` 카운트업.
 * - 이후 `target` 이 바뀔 때는 **현재 표시값 → 새 target** 으로 부드럽게 이행.
 *   (SSE 등 실시간 업데이트에서 매번 0 부터 다시 애니메이션해 "spinner" 처럼
 *    보이는 문제를 막는다.)
 */
export function useCountUp({
  target,
  duration = 700,
  delay = 0,
  start = 0,
  easing = linear,
}: UseCountUpOptions): number {
  const [current, setCurrent] = useState<number>(start);
  const currentRef = useRef<number>(start);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const delayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 매 렌더 시점의 최신 current 를 ref 에 스냅샷 — effect 안에서 from 값으로 사용.
  currentRef.current = current;

  useEffect(() => {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
    }
    if (delayTimerRef.current != null) {
      clearTimeout(delayTimerRef.current);
    }

    const fromValue = currentRef.current;
    const diff = target - fromValue;

    if (diff === 0) {
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
        const value = fromValue + diff * easedProgress;
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
    // `start` 는 첫 마운트의 초기값으로만 의미가 있으므로 dep 에서 제외.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration, delay, easing]);

  return current;
}
