"use client";

import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";
import { SecurityLogsSection } from "./SecurityLogsSection";
import { ActiveSessionsSection } from "./ActiveSessionsSection";
import { AccountSection } from "./AccountSection";
import { KisCredentialsSection } from "./KisCredentialsSection";
import { PushNotificationsSection } from "./PushNotificationsSection";
import { Card, CardContent } from "@/components/ui/card";

type Tab = "account" | "kis" | "notifications" | "security-logs" | "sessions";

const VALID_TABS: Tab[] = [
  "account",
  "kis",
  "notifications",
  "security-logs",
  "sessions",
];

const TABS: { id: Tab; label: string }[] = [
  { id: "account", label: "계정" },
  { id: "kis", label: "KIS 계좌" },
  { id: "notifications", label: "알림" },
  { id: "security-logs", label: "보안 로그" },
  { id: "sessions", label: "세션 관리" },
];

function readHashTab(): Tab {
  const hash = window.location.hash.slice(1) as Tab;
  return VALID_TABS.includes(hash) ? hash : "account";
}

function subscribeHash(callback: () => void): () => void {
  const handler = () => callback();
  window.addEventListener("hashchange", handler);
  return () => window.removeEventListener("hashchange", handler);
}

const getServerTab = (): Tab => "account";

export default function SettingsPage() {
  // The URL hash IS the source of truth for the active tab. useSyncExternalStore
  // keeps SSR and first client render aligned to "account" then switches to the
  // hash-derived tab post-hydration (no React 19 #418). Tab clicks update the
  // hash directly, which triggers the subscriber and re-renders.
  const activeTab = useSyncExternalStore(subscribeHash, readHashTab, getServerTab);

  const handleTabChange = useCallback((tab: Tab) => {
    if (window.location.hash.slice(1) === tab) return;
    window.location.hash = tab;
  }, []);

  // Scroll the active tab into view so the last tab ("세션 관리") never sits
  // clipped at the viewport edge on narrow screens.
  const tabRefs = useRef<Record<Tab, HTMLButtonElement | null>>({
    account: null,
    kis: null,
    notifications: null,
    "security-logs": null,
    sessions: null,
  });
  useEffect(() => {
    const el = tabRefs.current[activeTab];
    el?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [activeTab]);

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* Tab navigation — horizontal scroll on mobile so labels never wrap.
          overflow-y-hidden suppresses the vertical scrollbar that some
          browsers render alongside overflow-x-auto. */}
      <div className="-mx-4 overflow-x-auto overflow-y-hidden border-b px-4 sm:mx-0 sm:px-0">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              ref={(el) => {
                tabRefs.current[tab.id] = el;
              }}
              onClick={() => handleTabChange(tab.id)}
              className={`shrink-0 whitespace-nowrap px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Account tab */}
      {activeTab === "account" && <AccountSection />}

      {/* KIS credentials tab */}
      {activeTab === "kis" && <KisCredentialsSection />}

      {/* Notifications tab */}
      {activeTab === "notifications" && <PushNotificationsSection />}

      {/* Security logs tab */}
      {activeTab === "security-logs" && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="text-base font-semibold">보안 로그</h2>
            <p className="text-xs text-muted-foreground">최근 50건의 보안 이벤트를 표시합니다.</p>
            <SecurityLogsSection />
          </CardContent>
        </Card>
      )}

      {/* Sessions tab */}
      {activeTab === "sessions" && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <h2 className="text-base font-semibold">활성 세션</h2>
            <p className="text-xs text-muted-foreground">현재 로그인된 세션 목록입니다. 알 수 없는 세션은 즉시 취소하세요.</p>
            <ActiveSessionsSection />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
