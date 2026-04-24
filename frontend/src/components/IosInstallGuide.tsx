"use client";

import { Share2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface IosInstallGuideProps {
  open: boolean;
  onClose: () => void;
}

export function IosInstallGuide({ open, onClose }: IosInstallGuideProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>홈 화면에 추가하기</DialogTitle>
          <DialogDescription>
            iOS Safari 에서는 아래 순서로 앱처럼 설치할 수 있어요.
          </DialogDescription>
        </DialogHeader>
        <ol className="mt-2 space-y-4 text-sm">
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              1
            </span>
            <span className="leading-relaxed">
              하단(또는 상단)의{" "}
              <span className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 align-middle text-xs">
                <Share2 className="size-3.5" aria-hidden /> 공유
              </span>{" "}
              버튼을 탭해요.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              2
            </span>
            <span className="leading-relaxed">
              목록에서 <strong>“홈 화면에 추가”</strong> 를 선택해요.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
              3
            </span>
            <span className="leading-relaxed">
              우측 상단 <strong>“추가”</strong> 를 누르면 홈 화면에 THE WEALTH
              아이콘이 생성돼요.
            </span>
          </li>
        </ol>
        <p className="mt-2 text-xs text-muted-foreground">
          설치 후에는 홈 화면에서 바로 실행할 수 있고, 푸시 알림도 받을 수
          있어요 (iOS 16.4+).
        </p>
      </DialogContent>
    </Dialog>
  );
}
