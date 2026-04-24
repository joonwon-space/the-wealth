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
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      {/* Notification bell — fixed top-right on mobile, top-right of content area on desktop */}
      <div className="fixed right-4 top-3 z-40 md:right-6">
        <NotificationBell />
      </div>
      <main
        // 모바일: 탭바(56px) + safe-area 여유. 데스크탑(md 이상): 일반 패딩.
        // overflow-x: hidden — 내부 테이블/차트의 1~2px 초과가 페이지 전체를
        // 가로로 흔드는 것을 막는다. 가로 스크롤이 필요한 섹션은 각자
        // `overflow-x-auto` 컨테이너를 쓴다.
        // data-scroll-container — usePullToRefresh 훅이 실제 스크롤러를 찾을 수 있게 힌트 제공.
        data-scroll-container=""
        className="flex-1 overflow-y-auto overflow-x-hidden p-4 pr-14 pt-14 pb-[calc(env(safe-area-inset-bottom,0px)+80px)] md:p-6 md:pr-16 md:pt-6 md:pb-6"
      >
        {children}
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
