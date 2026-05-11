"use client";

import { useState } from "react";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";
import { IosInstallGuide } from "@/components/IosInstallGuide";

const DISMISSED_KEY = "install-modal-dismissed-at";
const COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

const BENEFITS = [
  "앱처럼 빠르게 실행",
  "실시간 주가 알림 수신",
  "오프라인에서도 포트폴리오 확인",
] as const;

export function InstallPromptModal() {
  const { canInstall, isStandalone, isIos, promptInstall } = useInstallPrompt();
  const [visible, setVisible] = useState(() => {
    try {
      const dismissedAt = Number(localStorage.getItem(DISMISSED_KEY) || "0");
      return !dismissedAt || Date.now() - dismissedAt >= COOLDOWN_MS;
    } catch {
      return true;
    }
  });
  const [iosOpen, setIosOpen] = useState(false);

  const dismiss = () => {
    setVisible(false);
    try {
      localStorage.setItem(DISMISSED_KEY, String(Date.now()));
    } catch {
      // localStorage unavailable — modal stays closed for this session
    }
  };

  const handleInstall = async () => {
    if (isIos && !canInstall) {
      setIosOpen(true);
      return;
    }
    const outcome = await promptInstall();
    if (outcome === "accepted" || outcome === "dismissed") {
      dismiss();
    }
  };

  const shouldShow = visible && !isStandalone && (canInstall || isIos);

  if (!shouldShow) {
    return iosOpen ? (
      <IosInstallGuide open={iosOpen} onClose={() => setIosOpen(false)} />
    ) : null;
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/50 md:hidden animate-in fade-in duration-200"
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-label="앱 설치 안내"
        aria-modal="true"
        className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl border-t bg-card shadow-2xl md:hidden animate-in slide-in-from-bottom duration-300"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 20px)" }}
      >
        <div className="mx-auto mt-3 h-1 w-10 rounded-full bg-muted-foreground/25" />

        <div className="flex items-start gap-4 px-5 pt-5 pb-2">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary shadow-md">
            <span className="text-xl font-black text-primary-foreground tracking-tight">
              W
            </span>
          </div>
          <div className="min-w-0 flex-1 pt-1">
            <p className="text-base font-bold leading-tight">THE WEALTH</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
              홈 화면에 추가해서 앱처럼 사용하세요
            </p>
          </div>
          <button
            type="button"
            aria-label="닫기"
            onClick={dismiss}
            className="mt-1 flex h-7 w-7 items-center justify-center rounded-full bg-muted text-muted-foreground hover:bg-muted/80"
          >
            <X className="size-4" />
          </button>
        </div>

        <ul className="mx-5 my-3 space-y-2.5 rounded-xl bg-muted/50 p-4 text-sm">
          {BENEFITS.map((benefit) => (
            <li key={benefit} className="flex items-center gap-2.5">
              <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] text-primary">
                ✓
              </span>
              <span className="text-foreground/80">{benefit}</span>
            </li>
          ))}
        </ul>

        <div className="flex gap-3 px-5 pb-5">
          <Button variant="outline" className="h-12 flex-1" onClick={dismiss}>
            나중에
          </Button>
          <Button className="h-12 flex-1" onClick={handleInstall}>
            <Download className="mr-1.5 size-4" />
            {isIos && !canInstall ? "설치 방법 보기" : "홈 화면에 추가"}
          </Button>
        </div>
      </div>
      <IosInstallGuide open={iosOpen} onClose={() => setIosOpen(false)} />
    </>
  );
}
