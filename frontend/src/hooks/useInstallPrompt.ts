"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: readonly string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
  prompt(): Promise<void>;
}

export interface InstallPromptState {
  canInstall: boolean;
  isStandalone: boolean;
  isIos: boolean;
  promptInstall: () => Promise<"accepted" | "dismissed" | "unavailable">;
}

function detectIos(): boolean {
  const ua = window.navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) && !("MSStream" in window);
}

function detectStandaloneNow(): boolean {
  if (window.matchMedia("(display-mode: standalone)").matches) return true;
  const navAny = window.navigator as Navigator & { standalone?: boolean };
  return Boolean(navAny.standalone);
}

const STANDALONE_QUERY = "(display-mode: standalone)";

function subscribeStandalone(callback: () => void): () => void {
  const mql = window.matchMedia(STANDALONE_QUERY);
  const handler = () => callback();
  mql.addEventListener("change", handler);
  window.addEventListener("appinstalled", handler);
  return () => {
    mql.removeEventListener("change", handler);
    window.removeEventListener("appinstalled", handler);
  };
}

const subscribeIos = (): (() => void) => () => {};
const getServerFalse = (): boolean => false;

export function useInstallPrompt(): InstallPromptState {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  // useSyncExternalStore guarantees SSR returns false and the client reads the
  // live value post-hydration — keeps the first client render identical to
  // server output (avoids React 19 hydration mismatch #418).
  const isStandalone = useSyncExternalStore(
    subscribeStandalone,
    detectStandaloneNow,
    getServerFalse,
  );
  const isIos = useSyncExternalStore(subscribeIos, detectIos, getServerFalse);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    const installed = () => {
      setDeferredPrompt(null);
    };
    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", installed);
    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installed);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    if (!deferredPrompt) return "unavailable" as const;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    return outcome;
  }, [deferredPrompt]);

  return {
    canInstall: Boolean(deferredPrompt) && !isStandalone,
    isStandalone,
    isIos,
    promptInstall,
  };
}
