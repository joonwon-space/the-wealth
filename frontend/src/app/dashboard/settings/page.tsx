"use client";

import { useState } from "react";
import { SecurityLogsSection } from "./SecurityLogsSection";
import { ActiveSessionsSection } from "./ActiveSessionsSection";
import { AccountSection } from "./AccountSection";
import { KisCredentialsSection } from "./KisCredentialsSection";
import { Card, CardContent } from "@/components/ui/card";

type Tab = "account" | "kis" | "security-logs" | "sessions";

const TABS: { id: Tab; label: string }[] = [
  { id: "account", label: "계정" },
  { id: "kis", label: "KIS 계좌" },
  { id: "security-logs", label: "보안 로그" },
  { id: "sessions", label: "세션 관리" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("account");

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Account tab */}
      {activeTab === "account" && <AccountSection />}

      {/* KIS credentials tab */}
      {activeTab === "kis" && <KisCredentialsSection />}

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
