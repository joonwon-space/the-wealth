"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

function isStandaloneMode(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(display-mode: standalone)").matches) return true;
  const navAny = window.navigator as Navigator & { standalone?: boolean };
  return Boolean(navAny.standalone);
}

/**
 * A 300ms fade-in overlay shown only when the app launches in PWA standalone
 * mode. Browser tabs: no-op (standalone is false → initial state is false and
 * never flips on).
 */
export function AppSplash() {
  // Lazy init: read once on mount, avoid React 19 set-state-in-effect rule.
  const [visible, setVisible] = useState<boolean>(() => isStandaloneMode());

  useEffect(() => {
    if (!visible) return;
    const timer = window.setTimeout(() => setVisible(false), 300);
    return () => window.clearTimeout(timer);
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      aria-hidden
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background duration-300 animate-in fade-in"
    >
      <Image
        src="/icon-512.png"
        alt=""
        width={96}
        height={96}
        priority
        className="rounded-2xl"
      />
    </div>
  );
}
