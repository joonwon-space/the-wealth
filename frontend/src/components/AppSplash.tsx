"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

/**
 * A 300ms fade-in overlay shown only when the app launches in PWA standalone
 * mode. On browser tabs it's a no-op — users already see the page directly.
 */
export function AppSplash() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
    if (!standalone) return;
    setVisible(true);
    const timer = window.setTimeout(() => setVisible(false), 300);
    return () => window.clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div
      aria-hidden
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background animate-in fade-in duration-300"
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
