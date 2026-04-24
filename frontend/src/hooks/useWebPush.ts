"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type PermissionState = "default" | "granted" | "denied" | "unsupported";
type SubscribedState = "loading" | "subscribed" | "idle";

interface PushPublicKeyResponse {
  public_key: string;
  enabled: boolean;
}

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const buffer = new ArrayBuffer(raw.length);
  const view = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i++) view[i] = raw.charCodeAt(i);
  return buffer;
}

function isSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

function readPermission(): PermissionState {
  if (!isSupported()) return "unsupported";
  return Notification.permission as PermissionState;
}

export interface UseWebPush {
  supported: boolean;
  enabled: boolean;
  permission: PermissionState;
  status: SubscribedState;
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useWebPush(): UseWebPush {
  const supported = isSupported();
  // Lazy init to avoid React 19 set-state-in-effect.
  const [permission, setPermission] = useState<PermissionState>(() =>
    readPermission(),
  );
  const [status, setStatus] = useState<SubscribedState>("loading");
  const [enabled, setEnabled] = useState(false);

  const refresh = useCallback(async () => {
    if (!supported) {
      setStatus("idle");
      return;
    }
    try {
      const registration = await navigator.serviceWorker.ready;
      const existing = await registration.pushManager.getSubscription();
      setStatus(existing ? "subscribed" : "idle");
    } catch {
      setStatus("idle");
    }
  }, [supported]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<PushPublicKeyResponse>(
          "/push/public-key",
        );
        if (!cancelled) setEnabled(Boolean(data?.enabled));
      } catch {
        if (!cancelled) setEnabled(false);
      }
      if (!cancelled) await refresh();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const subscribe = useCallback(async () => {
    if (!supported) throw new Error("Web Push not supported in this browser");
    const { data } = await api.get<PushPublicKeyResponse>("/push/public-key");
    if (!data.enabled || !data.public_key) {
      throw new Error("서버에서 푸시 알림이 비활성화되어 있어요.");
    }

    const perm = await Notification.requestPermission();
    setPermission(perm as PermissionState);
    if (perm !== "granted") throw new Error("알림 권한이 필요합니다.");

    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.public_key),
      });
    }

    const raw = subscription.toJSON();
    await api.post("/push/subscribe", {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: raw.keys?.p256dh ?? "",
        auth: raw.keys?.auth ?? "",
      },
      user_agent: navigator.userAgent.slice(0, 255),
    });
    setStatus("subscribed");
  }, [supported]);

  const unsubscribe = useCallback(async () => {
    if (!supported) return;
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      setStatus("idle");
      return;
    }
    try {
      await api.delete(
        `/push/subscribe?endpoint=${encodeURIComponent(subscription.endpoint)}`,
      );
    } catch {
      // Server may have already dropped it; continue with client-side unsub.
    }
    await subscription.unsubscribe();
    setStatus("idle");
  }, [supported]);

  return { supported, enabled, permission, status, subscribe, unsubscribe, refresh };
}
