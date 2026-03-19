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
  const statusRef = useRef<StreamStatus>("disconnected");
  const [status, setStatusState] = useState<StreamStatus>("disconnected");
  // reconnectKey increments to force re-creation of EventSource
  const [reconnectKey, setReconnectKey] = useState(0);
  // Access token from Zustand memory state (set after login, not from localStorage)
  const accessToken = useAuthStore((s) => s.accessToken);

  /** Update both the ref (immediate) and the state (triggers re-render). */
  const setStatus = useCallback((next: StreamStatus) => {
    statusRef.current = next;
    setStatusState(next);
  }, []);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    if (!accessToken) return;

    // EventSource는 Authorization 헤더를 지원하지 않으므로 query param으로 토큰 전달
    const url = `${API_BASE}/prices/stream?token=${encodeURIComponent(accessToken)}`;
    const es = new EventSource(url);
    esRef.current = es;

    // Reflect the initial connecting state via the open callback chain.
    // We set status inside event handlers (not synchronously in the effect body)
    // to satisfy react-hooks/set-state-in-effect lint rule.
    const handleOpen = () => {
      setStatus("connected");
    };

    const handleMessage = (e: MessageEvent) => {
      // Promote to "connected" on first message if not already (handles cases
      // where onopen doesn't fire before the first message).
      if (statusRef.current !== "connected") {
        setStatus("connected");
      }
      try {
        const data = JSON.parse(e.data) as PriceStreamEvent;
        if (data.prices && Object.keys(data.prices).length > 0) {
          onPrices(data.prices);
        }
      } catch {
        // ignore parse errors
      }
    };

    const handleError = () => {
      es.close();
      esRef.current = null;
      setStatus("disconnected");
    };

    es.onopen = handleOpen;
    es.onmessage = handleMessage;
    es.onerror = handleError;

    // Mark as connecting by scheduling a microtask so the state update
    // happens after the effect body completes (avoids synchronous setState in effect).
    queueMicrotask(() => {
      if (esRef.current === es) {
        setStatus("connecting");
      }
    });

    return () => {
      es.close();
      esRef.current = null;
      setStatus("disconnected");
    };
  }, [enabled, onPrices, accessToken, reconnectKey, setStatus]);

  const reconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setReconnectKey((k) => k + 1);
  }, []);

  return { status, reconnect };
}
