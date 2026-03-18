"use client";

import { useEffect, useRef } from "react";
import { useAuthStore } from "@/store/auth";

const API_HOST = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE = `${API_HOST}/api/v1`;

interface PriceStreamEvent {
  market_open?: boolean;
  prices?: Record<string, string>;
  error?: string;
}

interface Options {
  onPrices: (prices: Record<string, string>) => void;
  enabled?: boolean;
}

/**
 * SSE 실시간 가격 스트림 훅.
 * 시장 개장 시간(KST 09:00~15:30)에만 서버에서 가격을 push한다.
 * enabled=false 이면 연결하지 않는다.
 */
export function usePriceStream({ onPrices, enabled = true }: Options): void {
  const esRef = useRef<EventSource | null>(null);
  // Access token from Zustand memory state (set after login, not from localStorage)
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    if (!accessToken) return;

    // EventSource는 Authorization 헤더를 지원하지 않으므로 query param으로 토큰 전달
    const url = `${API_BASE}/prices/stream?token=${encodeURIComponent(accessToken)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as PriceStreamEvent;
        if (data.prices && Object.keys(data.prices).length > 0) {
          onPrices(data.prices);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [enabled, onPrices, accessToken]);
}
