"use client";

import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <WifiOff className="size-8 text-muted-foreground" aria-hidden />
      </div>
      <div className="space-y-2">
        <h1 className="text-xl font-semibold">오프라인 상태입니다</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          네트워크 연결이 복구되면 자동으로 최신 데이터를 가져옵니다. 최근에
          열었던 화면은 일부 캐시되어 있습니다.
        </p>
      </div>
      <Button
        onClick={() => {
          if (typeof window !== "undefined") window.location.reload();
        }}
        className="touch-target"
      >
        다시 시도
      </Button>
    </div>
  );
}
