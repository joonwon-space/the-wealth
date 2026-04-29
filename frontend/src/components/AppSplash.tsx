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
 * mode. Browser tabs: no-op.
 *
 * State starts `false` so SSR and the first client render emit identical DOM
 * (no hydration mismatch). The standalone check + auto-hide timer fire in
 * useEffect after mount.
 */
export function AppSplash() {
  const [visible, setVisible] = useState<boolean>(false);

  useEffect(() => {
    if (!isStandaloneMode()) return;
    // Cascading render is intentional: hydration must commit with the
    // server-equivalent `null` first, then the splash flashes in for 300ms.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setVisible(true);
    const timer = window.setTimeout(() => setVisible(false), 300);
    return () => window.clearTimeout(timer);
  }, []);

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
