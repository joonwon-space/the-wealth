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
      <main
        // overflow-x: hidden — 내부 테이블/차트의 1~2px 초과가 페이지 전체를
        // 가로로 흔드는 것을 막는다. 가로 스크롤이 필요한 섹션은 각자
        // `overflow-x-auto` 컨테이너를 쓴다.
        // data-scroll-container — usePullToRefresh 훅이 실제 스크롤러를 찾을 수 있게 힌트 제공.
        data-scroll-container=""
        className="flex-1 overflow-y-auto overflow-x-hidden"
      >
        {/* Sticky top bar — 알림 벨만 탑재. 모바일에선 왼쪽의 fixed 햄버거 버튼이
            이 바 위에 떠 있다(z-50 > 탑바 z-30). 탑바를 main 흐름 안에 두면
            각 페이지의 액션 버튼과 벨이 서로 겹치지 않고, 벨 아래로 빈 가로
            스트립이 생기지도 않는다.

            pl-14 — 햄버거 버튼이 absolute 로 왼쪽을 차지하므로 탑바 안의 콘텐츠는
            모바일에서 pl-14 로 안전 영역을 확보. md 이상에선 햄버거 없음 → pl-6. */}
        <div className="sticky top-0 z-30 flex min-h-16 items-center justify-end border-b bg-background/90 pl-14 pr-4 backdrop-blur-md md:min-h-14 md:pl-6 md:pr-6">
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
