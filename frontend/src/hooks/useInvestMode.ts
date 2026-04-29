"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { InvestMode } from "@/components/mode-toggle";

const STORAGE_KEY = "thewealth.invest-mode";
const CHANGE_EVENT = "thewealth:invest-mode-change";

function readSavedMode(): InvestMode {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "long" || saved === "short") return saved;
  } catch {
    // localStorage unavailable (private mode, etc.) — fall through
  }
  return "long";
}

function subscribe(callback: () => void): () => void {
  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener(CHANGE_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(CHANGE_EVENT, handler);
  };
}

const getServerSnapshot = (): InvestMode => "long";

/**
 * Dual-brain 모드(장기/단타)를 localStorage 에 persist.
 *
 * `useSyncExternalStore` 로 SSR 안전한 hydration 보장 — 서버는 항상 'long' 을
 * 반환하고 클라이언트는 마운트 후 localStorage 값을 사용한다. lazy `useState`
 * 초기화로 localStorage 를 읽으면 SSR/CSR 결과가 달라 React 19 hydration
 * mismatch (#418) 가 발생하므로 사용 금지.
 */
export function useInvestMode(): [InvestMode, (m: InvestMode) => void] {
  const mode = useSyncExternalStore(subscribe, readSavedMode, getServerSnapshot);

  const setMode = useCallback((next: InvestMode) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
    // Notify subscribers in the same tab — `storage` event fires only across
    // tabs, so we dispatch a custom event to refresh local subscribers too.
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }, []);

  return [mode, setMode];
}
