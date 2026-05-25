"use client";

import { useState } from "react";
import { MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { Scenario } from "./types";

interface Props {
  scenarios: Scenario[];
  activeId: string;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
}

export function ScenarioTabs({
  scenarios,
  activeId,
  onSelect,
  onAdd,
  onRename,
  onDelete,
}: Props) {
  const [renameTarget, setRenameTarget] = useState<Scenario | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Scenario | null>(null);

  const canDelete = scenarios.length > 1;

  const openRename = (s: Scenario) => {
    setRenameDraft(s.name);
    setRenameTarget(s);
  };

  const commitRename = () => {
    if (renameTarget && renameDraft.trim()) {
      onRename(renameTarget.id, renameDraft.trim());
    }
    setRenameTarget(null);
  };

  return (
    <>
      <div className="flex items-center gap-1 overflow-x-auto border-b">
        {scenarios.map((s) => {
          const active = s.id === activeId;
          return (
            <div
              key={s.id}
              className={cn(
                "group relative flex items-center gap-1 border-b-2 px-3 py-2 transition-colors",
                active
                  ? "border-foreground text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(s.id)}
                className="text-sm font-medium whitespace-nowrap"
              >
                {s.name}
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger
                  aria-label={`${s.name} 옵션`}
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:bg-muted",
                    !active && "opacity-0 group-hover:opacity-100",
                  )}
                >
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={() => openRename(s)}>
                    <Pencil className="h-3.5 w-3.5" />
                    이름 변경
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!canDelete}
                    onClick={() => setDeleteTarget(s)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    삭제
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        })}
        <Button
          variant="ghost"
          size="sm"
          onClick={onAdd}
          className="h-8 gap-1 px-2 text-muted-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          시나리오
        </Button>
      </div>

      {/* Rename Dialog */}
      <Dialog
        open={renameTarget !== null}
        onOpenChange={(o) => !o && setRenameTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>시나리오 이름 변경</DialogTitle>
          </DialogHeader>
          <Input
            value={renameDraft}
            onChange={(e) => setRenameDraft(e.target.value)}
            maxLength={40}
            placeholder="예: 준원 개인연금"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitRename();
              }
            }}
            autoFocus
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)}>
              취소
            </Button>
            <Button onClick={commitRename}>변경</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              &lsquo;{deleteTarget?.name}&rsquo; 시나리오를 삭제할까요?
            </AlertDialogTitle>
            <AlertDialogDescription>
              이 시나리오의 모든 행과 메타 설정이 영구 삭제됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (deleteTarget) onDelete(deleteTarget.id);
                setDeleteTarget(null);
              }}
            >
              삭제
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
