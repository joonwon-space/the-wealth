"use client";

import { useEffect } from "react";
import { toast } from "sonner";

/**
 * Registers the service worker (production only) and surfaces a Sonner toast
 * when a new version is waiting. Clicking the toast posts `SKIP_WAITING` and
 * reloads the page so the new SW takes control.
 */
export function ServiceWorkerUpdateToast() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;
    if (process.env.NODE_ENV !== "production") return;

    let refreshing = false;
    const onControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener(
      "controllerchange",
      onControllerChange,
    );

    const promptUpdate = (registration: ServiceWorkerRegistration) => {
      toast("새 버전이 준비됐어요", {
        description: "새로고침하면 최신 앱으로 업데이트됩니다.",
        action: {
          label: "새로고침",
          onClick: () => {
            registration.waiting?.postMessage({ type: "SKIP_WAITING" });
          },
        },
        duration: 12_000,
      });
    };

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        if (registration.waiting) promptUpdate(registration);
        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener("statechange", () => {
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              promptUpdate(registration);
            }
          });
        });
      })
      .catch((error: unknown) => {
        console.warn("SW registration failed", error);
      });

    return () => {
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        onControllerChange,
      );
    };
  }, []);

  return null;
}
