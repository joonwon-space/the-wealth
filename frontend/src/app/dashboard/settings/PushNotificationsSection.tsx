"use client";

import { useState } from "react";
import { Bell, BellOff, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useWebPush } from "@/hooks/useWebPush";

export function PushNotificationsSection() {
  const { supported, enabled, permission, status, subscribe, unsubscribe } =
    useWebPush();
  const [busy, setBusy] = useState(false);

  const handleSubscribe = async () => {
    setBusy(true);
    try {
      await subscribe();
      toast.success("모바일 푸시 알림을 켰어요.");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "알림 구독에 실패했어요.";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  const handleUnsubscribe = async () => {
    setBusy(true);
    try {
      await unsubscribe();
      toast.success("모바일 푸시 알림을 껐어요.");
    } catch {
      toast.error("구독 해제에 실패했어요.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {status === "subscribed" ? (
              <Bell className="size-5" />
            ) : (
              <BellOff className="size-5" />
            )}
          </div>
          <div className="flex-1 space-y-1">
            <h2 className="text-base font-semibold">모바일 푸시 알림</h2>
            <p className="text-xs text-muted-foreground">
              가격 알림, 체결 알림을 홈 화면에 추가한 브라우저/앱에 즉시
              전달합니다. iOS 는 홈 화면에 추가한 상태에서만 받을 수 있어요.
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-[120px_1fr] gap-y-1 text-xs">
          <dt className="text-muted-foreground">브라우저 지원</dt>
          <dd>
            {supported ? (
              <span className="inline-flex items-center gap-1 text-foreground">
                <CheckCircle2 className="size-3.5 text-primary" /> 지원됨
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <XCircle className="size-3.5" /> 미지원 (iOS Safari 는 홈
                화면에 추가 필요)
              </span>
            )}
          </dd>
          <dt className="text-muted-foreground">서버 설정</dt>
          <dd>
            {enabled ? (
              <span className="inline-flex items-center gap-1 text-foreground">
                <CheckCircle2 className="size-3.5 text-primary" /> 활성
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <XCircle className="size-3.5" /> 비활성 (VAPID 미설정)
              </span>
            )}
          </dd>
          <dt className="text-muted-foreground">현재 상태</dt>
          <dd className="text-foreground">
            {status === "loading"
              ? "확인 중…"
              : status === "subscribed"
                ? "구독 중"
                : "미구독"}
            {permission === "denied" && (
              <span className="ml-2 text-fall">권한 거부됨 — 브라우저 설정에서 허용해 주세요.</span>
            )}
          </dd>
        </dl>

        <div className="flex justify-end gap-2">
          {status === "subscribed" ? (
            <Button
              variant="outline"
              onClick={handleUnsubscribe}
              disabled={busy}
            >
              알림 끄기
            </Button>
          ) : (
            <Button
              onClick={handleSubscribe}
              disabled={busy || !supported || !enabled || permission === "denied"}
            >
              알림 켜기
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
