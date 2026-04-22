"use client";

import { useCallback, useEffect, useState } from "react";
import type { InvestMode } from "@/components/mode-toggle";

const STORAGE_KEY = "thewealth.invest-mode";

/**
 * Dual-brain 모드(장기/단타)를 localStorage 에 persist. 서버 초기 렌더에는
 * "long" 이 기본값이고, 마운트 후 클라이언트 저장값이 반영된다.
 */
export function useInvestMode(): [InvestMode, (m: InvestMode) => void] {
  const [mode, setModeState] = useState<InvestMode>("long");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "long" || saved === "short") {
        setModeState(saved);
      }
    } catch {
      // localStorage not available
    }
  }, []);

  const setMode = useCallback((next: InvestMode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  return [mode, setMode];
}
