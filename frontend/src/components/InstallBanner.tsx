"use client";

import { useEffect, useRef, useState } from "react";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";
import { IosInstallGuide } from "@/components/IosInstallGuide";

const DISMISSED_KEY = "install-banner-dismissed-at";
const VISIT_COUNTER_KEY = "install-banner-visits";
const COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000; // 30 days
const VISITS_REQUIRED = 2;

interface BannerEligibility {
  eligible: boolean;
}

/**
 * Reads persisted visit count / dismissal, bumps the counter exactly once per
 * component mount, and returns whether the banner is eligible to show. Lazily
 * evaluated so React 19's `set-state-in-effect` rule is satisfied.
 */
function useBannerEligibility(): BannerEligibility {
  const [eligible] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      const dismissedAt = Number(
        window.localStorage.getItem(DISMISSED_KEY) || "0",
      );
      if (dismissedAt && Date.now() - dismissedAt < COOLDOWN_MS) return false;
      const prevVisits = Number(
        window.localStorage.getItem(VISIT_COUNTER_KEY) || "0",
      );
      const nextVisits = prevVisits + 1;
      window.localStorage.setItem(VISIT_COUNTER_KEY, String(nextVisits));
      return nextVisits >= VISITS_REQUIRED;
    } catch {
      return false;
    }
  });
  return { eligible };
}

export function InstallBanner() {
  const { canInstall, isStandalone, isIos, promptInstall } = useInstallPrompt();
  const { eligible } = useBannerEligibility();
  const [dismissed, setDismissed] = useState(false);
  const [iosOpen, setIosOpen] = useState(false);

  // Derived visibility — not state — avoids the set-state-in-effect rule.
  const shouldShow =
    !dismissed && !isStandalone && eligible && (canInstall || isIos);

  const dismissedOnce = useRef(false);
  useEffect(() => {
    if (!dismissed || dismissedOnce.current) return;
    dismissedOnce.current = true;
    try {
      window.localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    } catch {
      // ignore
    }
  }, [dismissed]);

  const handleInstall = async () => {
    if (isIos && !canInstall) {
      setIosOpen(true);
      return;
    }
    const outcome = await promptInstall();
    if (outcome === "accepted" || outcome === "dismissed") {
      setDismissed(true);
    }
  };

  if (!shouldShow) {
    return isIos ? (
      <IosInstallGuide open={iosOpen} onClose={() => setIosOpen(false)} />
    ) : null;
  }

  return (
    <>
      <div
        role="dialog"
        aria-label="앱 설치 안내"
        className="fixed left-3 right-3 z-50 rounded-2xl border bg-card shadow-lg md:hidden"
        style={{
          bottom: `calc(env(safe-area-inset-bottom, 0px) + 72px)`,
        }}
      >
        <div className="flex items-center gap-3 p-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Download className="size-5" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
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
            onClick={() => setDismissed(true)}
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
