"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Loader2, Moon, Pencil, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface UserMe {
  id: number;
  email: string;
  name: string | null;
}

export function AccountSection() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const { theme, setTheme } = useTheme();

  // Account info
  const { data: userMe } = useQuery<UserMe>({
    queryKey: ["users", "me"],
    queryFn: () => api.get<UserMe>("/users/me").then((r) => r.data),
  });
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const nameInputRef = useRef<HTMLInputElement>(null);
  const updateNameMutation = useMutation({
    mutationFn: (name: string) =>
      api.patch<UserMe>("/users/me", { name: name || null }),
    onSuccess: (resp) => {
      queryClient.setQueryData<UserMe>(["users", "me"], resp.data);
      setEditingName(false);
      toast.success("이름이 저장되었습니다");
    },
    onError: () => toast.error("저장에 실패했습니다"),
  });

  const handleNameSave = () => {
    updateNameMutation.mutate(nameInput.trim());
  };

  const handleNameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleNameSave();
    if (e.key === "Escape") setEditingName(false);
  };

  // Password change dialog
  const [pwDialogOpen, setPwDialogOpen] = useState(false);
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const [pwError, setPwError] = useState<string | null>(null);
  const changePwMutation = useMutation({
    mutationFn: () =>
      api.post("/users/me/change-password", {
        current_password: pwForm.current,
        new_password: pwForm.next,
      }),
    onSuccess: () => {
      toast.success("비밀번호가 변경되었습니다");
      setPwDialogOpen(false);
      setPwForm({ current: "", next: "", confirm: "" });
      setPwError(null);
    },
    onError: (err: unknown) => {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { error?: { message?: string } } } })
              .response?.data?.error?.message
          : null;
      setPwError(msg ?? "비밀번호 변경에 실패했습니다");
    },
  });

  const handleChangePw = () => {
    setPwError(null);
    if (pwForm.next.length < 8) {
      setPwError("새 비밀번호는 8자 이상이어야 합니다");
      return;
    }
    if (pwForm.next !== pwForm.confirm) {
      setPwError("새 비밀번호가 일치하지 않습니다");
      return;
    }
    changePwMutation.mutate();
  };

  // Email change dialog
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailForm, setEmailForm] = useState({ newEmail: "", password: "" });
  const [emailError, setEmailError] = useState<string | null>(null);
  const changeEmailMutation = useMutation({
    mutationFn: () =>
      api.post("/users/me/change-email", {
        new_email: emailForm.newEmail,
        current_password: emailForm.password,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users", "me"] });
      toast.success("이메일이 변경되었습니다");
      setEmailDialogOpen(false);
      setEmailForm({ newEmail: "", password: "" });
      setEmailError(null);
    },
    onError: (err: unknown) => {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { error?: { message?: string } } } })
              .response?.data?.error?.message
          : null;
      setEmailError(msg ?? "이메일 변경에 실패했습니다");
    },
  });

  // Delete account dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const deleteAccountMutation = useMutation({
    mutationFn: () =>
      api.delete("/users/me", { data: { current_password: deletePassword } }),
    onSuccess: () => {
      toast.success("계정이 삭제되었습니다");
      logout();
      router.push("/login");
    },
    onError: (err: unknown) => {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { error?: { message?: string } } } })
              .response?.data?.error?.message
          : null;
      setDeleteError(msg ?? "계정 삭제에 실패했습니다");
    },
  });

  // Focus name input when editing starts
  useEffect(() => {
    if (editingName) {
      nameInputRef.current?.focus();
    }
  }, [editingName]);

  return (
    <div className="space-y-6">
      {/* 계정 정보 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <h2 className="text-base font-semibold">계정 정보</h2>

          {/* 이메일 (읽기 전용) */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">이메일</p>
            <p className="text-sm font-medium">{userMe?.email ?? "—"}</p>
          </div>

          {/* 이름 인라인 편집 */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">이름</p>
            {editingName ? (
              <div className="flex items-center gap-2">
                <Input
                  ref={nameInputRef}
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onBlur={handleNameSave}
                  onKeyDown={handleNameKeyDown}
                  className="h-8 text-sm max-w-[200px]"
                  placeholder="이름 입력"
                  autoFocus
                />
                <button
                  onClick={handleNameSave}
                  disabled={updateNameMutation.isPending}
                  className="flex min-h-[32px] items-center gap-1 rounded px-2 text-xs font-medium text-primary hover:bg-accent disabled:opacity-50"
                >
                  {updateNameMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Check className="h-3 w-3" />
                  )}
                  저장
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setNameInput(userMe?.name ?? "");
                  setEditingName(true);
                }}
                className="flex items-center gap-1.5 text-sm font-medium hover:text-primary transition-colors group"
              >
                <span>{userMe?.name ?? "이름 없음"}</span>
                <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            )}
          </div>

          {/* 비밀번호 / 이메일 변경 버튼 영역 */}
          <div className="pt-2 border-t border-border/50 flex flex-wrap gap-2">
            {/* 이메일 변경 Dialog */}
            <Dialog open={emailDialogOpen} onOpenChange={(open) => {
              setEmailDialogOpen(open);
              if (!open) {
                setEmailForm({ newEmail: "", password: "" });
                setEmailError(null);
              }
            }}>
              <DialogTrigger render={<Button variant="outline" size="sm" className="text-xs" />}>
                이메일 변경
              </DialogTrigger>
              <DialogContent className="max-w-sm">
                <DialogHeader>
                  <DialogTitle>이메일 변경</DialogTitle>
                  <DialogDescription>새 이메일 주소와 현재 비밀번호를 입력하세요.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2">
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">새 이메일</label>
                    <Input
                      type="email"
                      value={emailForm.newEmail}
                      onChange={(e) => setEmailForm((f) => ({ ...f, newEmail: e.target.value }))}
                      placeholder="new@example.com"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">현재 비밀번호</label>
                    <Input
                      type="password"
                      value={emailForm.password}
                      onChange={(e) => setEmailForm((f) => ({ ...f, password: e.target.value }))}
                      placeholder="현재 비밀번호"
                    />
                  </div>
                  {emailError && (
                    <p className="text-xs text-destructive">{emailError}</p>
                  )}
                </div>
                <DialogFooter>
                  <Button
                    onClick={() => changeEmailMutation.mutate()}
                    disabled={changeEmailMutation.isPending || !emailForm.newEmail || !emailForm.password}
                    size="sm"
                  >
                    {changeEmailMutation.isPending && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                    변경
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* 비밀번호 변경 Dialog */}
            <Dialog open={pwDialogOpen} onOpenChange={(open) => {
              setPwDialogOpen(open);
              if (!open) {
                setPwForm({ current: "", next: "", confirm: "" });
                setPwError(null);
              }
            }}>
              <DialogTrigger render={<Button variant="outline" size="sm" className="text-xs" />}>
                비밀번호 변경
              </DialogTrigger>
              <DialogContent className="max-w-sm">
                <DialogHeader>
                  <DialogTitle>비밀번호 변경</DialogTitle>
                  <DialogDescription>새 비밀번호는 8자 이상이어야 합니다.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2">
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">현재 비밀번호</label>
                    <Input
                      type="password"
                      value={pwForm.current}
                      onChange={(e) => setPwForm((p) => ({ ...p, current: e.target.value }))}
                      placeholder="현재 비밀번호"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">새 비밀번호</label>
                    <Input
                      type="password"
                      value={pwForm.next}
                      onChange={(e) => setPwForm((p) => ({ ...p, next: e.target.value }))}
                      placeholder="새 비밀번호 (8자 이상)"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">새 비밀번호 확인</label>
                    <Input
                      type="password"
                      value={pwForm.confirm}
                      onChange={(e) => setPwForm((p) => ({ ...p, confirm: e.target.value }))}
                      placeholder="새 비밀번호 재입력"
                    />
                  </div>
                  {pwError && (
                    <p className="text-xs text-destructive">{pwError}</p>
                  )}
                </div>
                <DialogFooter>
                  <Button
                    onClick={handleChangePw}
                    disabled={changePwMutation.isPending || !pwForm.current || !pwForm.next}
                    size="sm"
                  >
                    {changePwMutation.isPending && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                    변경
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* 테마 */}
      <Card>
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">테마</p>
            <p className="text-xs text-muted-foreground">라이트 / 다크 모드 전환</p>
          </div>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex min-h-[44px] items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "라이트 모드" : "다크 모드"}
          </button>
        </CardContent>
      </Card>

      {/* 위험 구역 — 계정 삭제 */}
      <Card className="border-destructive/40">
        <CardContent className="space-y-3 p-6">
          <h2 className="text-base font-semibold text-destructive">위험 구역</h2>
          <p className="text-sm text-muted-foreground">
            계정을 삭제하면 모든 포트폴리오, 보유 종목, 거래 내역이 영구적으로 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
          </p>
          <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
            setDeleteDialogOpen(open);
            if (!open) {
              setDeletePassword("");
              setDeleteError(null);
            }
          }}>
            <DialogTrigger render={<Button variant="outline" size="sm" className="border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground text-xs" />}>
              계정 삭제
            </DialogTrigger>
            <DialogContent className="max-w-sm">
              <DialogHeader>
                <DialogTitle className="text-destructive">계정 영구 삭제</DialogTitle>
                <DialogDescription>
                  이 작업은 되돌릴 수 없습니다. 계속하려면 현재 비밀번호를 입력하세요.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3 py-2">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">현재 비밀번호</label>
                  <Input
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="현재 비밀번호"
                  />
                </div>
                {deleteError && (
                  <p className="text-xs text-destructive">{deleteError}</p>
                )}
              </div>
              <DialogFooter>
                <Button
                  variant="destructive"
                  onClick={() => deleteAccountMutation.mutate()}
                  disabled={deleteAccountMutation.isPending || !deletePassword}
                  size="sm"
                >
                  {deleteAccountMutation.isPending && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                  영구 삭제
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
