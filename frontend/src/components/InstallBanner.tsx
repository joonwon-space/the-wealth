"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";
import { IosInstallGuide } from "@/components/IosInstallGuide";

const DISMISSED_KEY = "install-banner-dismissed-at";
const VISIT_COUNTER_KEY = "install-banner-visits";
const COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000; // 30 days
const VISITS_REQUIRED = 2;

function readVisitCount(): number {
  try {
    return Number(window.localStorage.getItem(VISIT_COUNTER_KEY) || "0");
  } catch {
    return 0;
  }
}

function bumpVisitCount(): number {
  try {
    const next = readVisitCount() + 1;
    window.localStorage.setItem(VISIT_COUNTER_KEY, String(next));
    return next;
  } catch {
    return 0;
  }
}

function isWithinCooldown(): boolean {
  try {
    const raw = window.localStorage.getItem(DISMISSED_KEY);
    if (!raw) return false;
    const dismissedAt = Number(raw);
    if (Number.isNaN(dismissedAt)) return false;
    return Date.now() - dismissedAt < COOLDOWN_MS;
  } catch {
    return false;
  }
}

export function InstallBanner() {
  const { canInstall, isStandalone, isIos, promptInstall } = useInstallPrompt();
  const [visible, setVisible] = useState(false);
  const [iosOpen, setIosOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isStandalone) return;
    if (isWithinCooldown()) return;
    const visits = bumpVisitCount();
    if (visits < VISITS_REQUIRED) return;
    // iOS: show banner even without beforeinstallprompt (we'll open guide).
    if (!canInstall && !isIos) return;
    setVisible(true);
  }, [canInstall, isIos, isStandalone]);

  const dismiss = () => {
    try {
      window.localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    } catch {
      // ignore
    }
    setVisible(false);
  };

  const handleInstall = async () => {
    if (isIos && !canInstall) {
      setIosOpen(true);
      return;
    }
    const outcome = await promptInstall();
    if (outcome === "accepted" || outcome === "dismissed") {
      setVisible(false);
    }
  };

  if (!visible) {
    return isIos ? (
      <IosInstallGuide open={iosOpen} onClose={() => setIosOpen(false)} />
    ) : null;
  }

  return (
    <>
      <div
        role="dialog"
        aria-label="앱 설치 안내"
        // Sit above the bottom nav on mobile; hide on desktop since A2HS is UX-irrelevant there.
        className="fixed left-3 right-3 z-50 rounded-2xl border bg-card shadow-lg md:hidden"
        style={{
          bottom: `calc(env(safe-area-inset-bottom, 0px) + 72px)`,
        }}
      >
        <div className="flex items-center gap-3 p-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Download className="size-5" aria-hidden />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold">홈 화면에 THE WEALTH 추가</p>
            <p className="truncate text-xs text-muted-foreground">
              앱처럼 빠르게 실행하고 알림도 받아보세요.
            </p>
          </div>
          <Button size="sm" className="touch-target" onClick={handleInstall}>
            {isIos && !canInstall ? "방법 보기" : "설치"}
          </Button>
          <button
            type="button"
            aria-label="닫기"
            onClick={dismiss}
            className="touch-target flex items-center justify-center text-muted-foreground hover:text-foreground"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>
      </div>
      <IosInstallGuide open={iosOpen} onClose={() => setIosOpen(false)} />
    </>
  );
}
