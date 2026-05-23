"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: (birthYear: number) => void;
}

export function BirthYearDialog({ open, onClose, onSaved }: Props) {
  const currentYear = new Date().getFullYear();
  const [birthYear, setBirthYear] = useState<string>(String(currentYear - 30));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const n = Number(birthYear);
    if (!Number.isInteger(n) || n < 1900 || n > currentYear) {
      toast.error("생년은 1900 ~ 현재 연도 사이의 값이어야 합니다.");
      return;
    }
    setSaving(true);
    try {
      await api.put("/users/me/birth-year", { birth_year: n });
      onSaved(n);
      onClose();
    } catch {
      toast.error("저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>생년 입력</DialogTitle>
          <DialogDescription>
            연도별 수익률 표와 시뮬레이션에서 나이를 함께 표시하기 위해 필요합니다.
            지금 건너뛰어도 메뉴 사용에는 영향이 없습니다.
          </DialogDescription>
        </DialogHeader>
        <Input
          type="number"
          min={1900}
          max={currentYear}
          step={1}
          value={birthYear}
          onChange={(e) => setBirthYear(e.target.value)}
        />
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            나중에
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "저장 중..." : "저장"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
