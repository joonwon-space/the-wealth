"use client";

import { useState } from "react";
import Link from "next/link";
import { GripVertical, Pencil, Plus, Trash2, Wallet } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api } from "@/lib/api";
import { formatKRW } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Portfolio {
  id: number;
  name: string;
  currency: string;
  display_order: number;
  created_at: string;
  holdings_count: number;
  total_invested: string;
}

const PORTFOLIOS_QUERY_KEY = ["portfolios"] as const;

async function fetchPortfolios(): Promise<Portfolio[]> {
  const { data } = await api.get<Portfolio[]>("/portfolios");
  return data;
}

function SortablePortfolioRow({
  portfolio,
  editingId,
  editName,
  onEditStart,
  onEditChange,
  onEditSave,
  onEditCancel,
  onDelete,
  renamePending,
}: {
  portfolio: Portfolio;
  editingId: number | null;
  editName: string;
  onEditStart: (id: number, name: string) => void;
  onEditChange: (name: string) => void;
  onEditSave: (id: number) => void;
  onEditCancel: () => void;
  onDelete: (id: number) => void;
  renamePending: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: portfolio.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isEditing = editingId === portfolio.id;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 hover:bg-muted/30 transition-colors"
    >
      {/* 드래그 핸들 */}
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab touch-none min-h-[44px] min-w-[44px] flex items-center justify-center text-muted-foreground/40 hover:text-muted-foreground active:cursor-grabbing"
        aria-label="순서 변경"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      {/* 아이콘 */}
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
        <Wallet className="h-4 w-4 text-primary" />
      </div>

      {/* 이름 + 통화 */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <div className="flex items-center gap-1">
            <Input
              value={editName}
              onChange={(e) => onEditChange(e.target.value)}
              className="h-7 w-40 text-sm"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") onEditSave(portfolio.id);
                if (e.key === "Escape") onEditCancel();
              }}
            />
            <Button
              size="sm"
              onClick={() => onEditSave(portfolio.id)}
              className="h-7 px-2 text-xs"
              disabled={renamePending}
            >
              OK
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onEditCancel}
              className="h-7 px-2 text-xs"
            >
              취소
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <Link
              href={`/dashboard/portfolios/${portfolio.id}`}
              className="font-semibold truncate hover:underline"
            >
              {portfolio.name}
            </Link>
            <button
              onClick={() => onEditStart(portfolio.id, portfolio.name)}
              className="shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center text-muted-foreground/40 hover:text-muted-foreground"
              aria-label={`${portfolio.name} 이름 편집`}
            >
              <Pencil className="h-3 w-3" />
            </button>
          </div>
        )}
        <p className="text-xs text-muted-foreground">{portfolio.currency}</p>
      </div>

      {/* 통계 */}
      <div className="hidden sm:flex flex-col items-end text-xs text-muted-foreground tabular-nums shrink-0">
        <span>{portfolio.holdings_count}개 종목</span>
        <span>{formatKRW(portfolio.total_invested)}</span>
      </div>

      {/* 삭제 */}
      <button
        onClick={() => onDelete(portfolio.id)}
        aria-label={`${portfolio.name} 삭제`}
        className="shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function PortfoliosPage() {
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const { data: portfolios = [], isLoading } = useQuery<Portfolio[]>({
    queryKey: PORTFOLIOS_QUERY_KEY,
    queryFn: fetchPortfolios,
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.patch<Portfolio>(`/portfolios/${id}`, { name }).then((r) => r.data),
    onSuccess: (updated) => {
      queryClient.setQueryData<Portfolio[]>(PORTFOLIOS_QUERY_KEY, (prev) =>
        prev ? prev.map((p) => (p.id === updated.id ? { ...p, name: updated.name } : p)) : []
      );
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/portfolios/${id}`),
    onSuccess: (_, id) => {
      queryClient.setQueryData<Portfolio[]>(PORTFOLIOS_QUERY_KEY, (prev) =>
        prev ? prev.filter((p) => p.id !== id) : []
      );
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (items: { id: number; display_order: number }[]) =>
      api.patch("/portfolios/reorder", { items }),
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = portfolios.findIndex((p) => p.id === active.id);
    const newIndex = portfolios.findIndex((p) => p.id === over.id);
    const reordered = arrayMove(portfolios, oldIndex, newIndex);

    // Optimistic update
    queryClient.setQueryData<Portfolio[]>(PORTFOLIOS_QUERY_KEY, reordered);

    // Persist to backend
    reorderMutation.mutate(
      reordered.map((p, i) => ({ id: p.id, display_order: i }))
    );
  };

  const handleDelete = (id: number) => {
    if (!confirm("포트폴리오를 삭제하시겠습니까?")) return;
    deleteMutation.mutate(id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">포트폴리오</h1>
        <Button onClick={() => setShowModal(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          새 포트폴리오
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border px-4 py-3">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-9 w-9 rounded-lg" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-12" />
              </div>
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      ) : portfolios.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <Wallet className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium">포트폴리오가 없습니다</p>
          <p className="mt-1 text-sm text-muted-foreground">
            새 포트폴리오를 만들어 종목을 추가하세요.
          </p>
          <Button onClick={() => setShowModal(true)} className="mt-4 gap-2">
            <Plus className="h-4 w-4" />
            새 포트폴리오
          </Button>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={portfolios.map((p) => p.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-2">
              {portfolios.map((p) => (
                <SortablePortfolioRow
                  key={p.id}
                  portfolio={p}
                  editingId={editingId}
                  editName={editName}
                  onEditStart={(id, name) => {
                    setEditingId(id);
                    setEditName(name);
                  }}
                  onEditChange={setEditName}
                  onEditSave={(id) => {
                    if (!editName.trim()) return;
                    renameMutation.mutate({ id, name: editName });
                  }}
                  onEditCancel={() => setEditingId(null)}
                  onDelete={handleDelete}
                  renamePending={renameMutation.isPending}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      <CreatePortfolioDialog
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreate={(p) => {
          queryClient.setQueryData<Portfolio[]>(PORTFOLIOS_QUERY_KEY, (prev) =>
            prev ? [...prev, p] : [p]
          );
          setShowModal(false);
        }}
      />
    </div>
  );
}

function CreatePortfolioDialog({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (p: Portfolio) => void;
}) {
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("KRW");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<Portfolio>("/portfolios", { name, currency });
      onCreate(data);
      setName("");
      setCurrency("KRW");
    } catch {
      setError("생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>새 포트폴리오</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="space-y-1">
            <label className="text-sm font-medium">이름</label>
            <Input
              autoFocus
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="내 포트폴리오"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">기준 통화</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="KRW">KRW — 한국 원</option>
              <option value="USD">USD — 미국 달러</option>
            </select>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={loading} className="flex-1">
              {loading ? "생성 중..." : "생성"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
