"use client";

import { useCallback, useState } from "react";
import type { InvestMode } from "@/components/mode-toggle";

const STORAGE_KEY = "thewealth.invest-mode";

function readSavedMode(): InvestMode {
  if (typeof window === "undefined") return "long";
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "long" || saved === "short") return saved;
  } catch {
    // localStorage unavailable (private mode, etc.) — fall through
  }
  return "long";
}

/**
 * Dual-brain 모드(장기/단타)를 localStorage 에 persist. React 19 Compiler 규칙에
 * 맞춰 lazy initial state 로 로드한다 — useEffect 에서 setState 하지 않는다.
 * SSR 경로에서는 기본값 'long' 으로 하이드레이트되고, 클라이언트 첫 렌더에서
 * localStorage 값으로 동기화된다.
 */
export function useInvestMode(): [InvestMode, (m: InvestMode) => void] {
  const [mode, setModeState] = useState<InvestMode>(readSavedMode);

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
