"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
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
 *
 * 인증 방식: POST /auth/sse-ticket으로 30초 TTL 단기 티켓을 발급받아
 * ?ticket= 쿼리 파라미터로 전달한다. JWT가 nginx 로그에 노출되지 않는다.
 */
export function usePriceStream({ onPrices, enabled = true }: Options): Result {
  const esRef = useRef<EventSource | null>(null);
  const statusRef = useRef<StreamStatus>("disconnected");
  const [status, setStatusState] = useState<StreamStatus>("disconnected");
  // reconnectKey increments to force re-creation of EventSource
  const [reconnectKey, setReconnectKey] = useState(0);
  // Access token presence — used only to detect login state (not sent in URL)
  const accessToken = useAuthStore((s) => s.accessToken);

  /** Update both the ref (immediate) and the state (triggers re-render). */
  const setStatus = useCallback((next: StreamStatus) => {
    statusRef.current = next;
    setStatusState(next);
  }, []);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    if (!accessToken) return;

    let cancelled = false;

    const connect = async (): Promise<void> => {
      let ticket: string;
      try {
        const resp = await api.post<{ ticket: string }>("/auth/sse-ticket");
        ticket = resp.data.ticket;
      } catch {
        // Ticket request failed — cannot connect
        if (!cancelled) setStatus("disconnected");
        return;
      }

      if (cancelled) return;

      // Use single-use ticket instead of JWT in URL — no credential exposure in server logs
      const url = `${API_BASE}/prices/stream?ticket=${encodeURIComponent(ticket)}`;
      const es = new EventSource(url);
      if (!cancelled) {
        esRef.current = es;
      } else {
        es.close();
        return;
      }

      const handleOpen = (): void => {
        setStatus("connected");
      };

      const handleMessage = (e: MessageEvent): void => {
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

      const handleError = (): void => {
        es.close();
        esRef.current = null;
        setStatus("disconnected");
      };

      es.onopen = handleOpen;
      es.onmessage = handleMessage;
      es.onerror = handleError;
    };

    queueMicrotask(() => {
      if (!cancelled) setStatus("connecting");
    });

    void connect();

    return () => {
      cancelled = true;
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
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
