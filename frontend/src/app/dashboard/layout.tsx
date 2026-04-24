"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { BottomNav } from "@/components/BottomNav";
import { NotificationBell } from "@/components/NotificationBell";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { KeyboardShortcutsDialog } from "@/components/KeyboardShortcutsDialog";
import { ServiceWorkerUpdateToast } from "@/components/ServiceWorkerUpdateToast";
import { InstallBanner } from "@/components/InstallBanner";
import { AppSplash } from "@/components/AppSplash";
import { MobilePullToRefresh } from "@/components/MobilePullToRefresh";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
      // Cmd+? (Cmd+Shift+/)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "/") {
        e.preventDefault();
        setShortcutsOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    // body 가 메인 스크롤러가 되도록 내부 스크롤을 쓰지 않는다. 이렇게 하면
    // iOS 에서 상단 status-bar 탭으로 페이지가 맨 위로 스크롤된다 (iOS 는
    // body/document 스크롤러에 대해서만 이 제스처를 적용).
    // 사이드바와 BottomNav 는 fixed 로 떠 있으므로 flex 래퍼도 불필요하다.
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="min-h-screen md:ml-60">
        {/* Sticky top bar — 알림 벨만 탑재. 모바일에선 왼쪽의 fixed 햄버거 버튼이
            이 바 위에 떠 있다(z-50 > 탑바 z-30). body 가 스크롤러이므로
            sticky top-0 은 뷰포트 상단에 고정된다. */}
        <div className="sticky top-0 z-20 flex min-h-16 items-center justify-end border-b bg-background/90 pl-14 pr-4 backdrop-blur-md md:min-h-14 md:pl-6 md:pr-6">
          <NotificationBell />
        </div>
        <div className="p-4 pb-[calc(env(safe-area-inset-bottom,0px)+80px)] md:p-6 md:pb-6">
          {children}
        </div>
      </main>
      <BottomNav />
      <InstallBanner />
      <AppSplash />
      <MobilePullToRefresh />
      <ServiceWorkerUpdateToast />
      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={() => setSearchOpen(false)}
      />
      <KeyboardShortcutsDialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  );
}
