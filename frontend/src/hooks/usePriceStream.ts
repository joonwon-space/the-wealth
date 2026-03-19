"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/store/auth";

const API_HOST = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE = `${API_HOST}/api/v1`;

interface PriceStreamEvent {
  market_open?: boolean;
  prices?: Record<string, string>;
  error?: string;
}

export type StreamStatus = "connecting" | "connected" | "disconnected";

interface Options {
  onPrices: (prices: Record<string, string>) => void;
  enabled?: boolean;
}

interface Result {
  status: StreamStatus;
  reconnect: () => void;
}

/**
 * SSE 실시간 가격 스트림 훅.
 * 시장 개장 시간(KST 09:00~15:30)에만 서버에서 가격을 push한다.
 * enabled=false 이면 연결하지 않는다.
 */
export function usePriceStream({ onPrices, enabled = true }: Options): Result {
  const esRef = useRef<EventSource | null>(null);
  const [status, setStatus] = useState<StreamStatus>("disconnected");
  // reconnectKey increments to force re-creation of EventSource
  const [reconnectKey, setReconnectKey] = useState(0);
  // Access token from Zustand memory state (set after login, not from localStorage)
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    if (!accessToken) return;

    setStatus("connecting");

    // EventSource는 Authorization 헤더를 지원하지 않으므로 query param으로 토큰 전달
    const url = `${API_BASE}/prices/stream?token=${encodeURIComponent(accessToken)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setStatus("connected");
    };

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
      setStatus("disconnected");
    };

    return () => {
      es.close();
      esRef.current = null;
      setStatus("disconnected");
    };
  }, [enabled, onPrices, accessToken, reconnectKey]);

  const reconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setReconnectKey((k) => k + 1);
  }, []);

  return { status, reconnect };
}
