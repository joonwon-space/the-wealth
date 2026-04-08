"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { holdingsKey } from "./HoldingsSection";
import type { Holding } from "./HoldingsSection";

export interface UseHoldingsInlineEditResult {
  editId: number | null;
  editForm: { quantity: string; avg_price: string };
  isEditPending: boolean;
  startEdit: (holding: Holding) => void;
  cancelEdit: () => void;
  setEditFormField: (field: "quantity" | "avg_price", value: string) => void;
  saveEdit: (holdingId: number) => void;
}

export function useHoldingsInlineEdit(portfolioId: number): UseHoldingsInlineEditResult {
  const queryClient = useQueryClient();
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ quantity: string; avg_price: string }>({
    quantity: "",
    avg_price: "",
  });

  const editHoldingMutation = useMutation({
    mutationFn: ({
      holdingId,
      quantity,
      avg_price,
    }: {
      holdingId: number;
      quantity: number;
      avg_price: number;
    }) =>
      api
        .patch<Holding>(`/portfolios/holdings/${holdingId}`, { quantity, avg_price })
        .then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData<Holding[]>(holdingsKey(portfolioId), (prev) =>
        prev ? prev.map((h) => (h.id === data.id ? data : h)) : []
      );
      setEditId(null);
    },
    onError: () => {
      toast.error("보유종목 수정에 실패했습니다. 잠시 후 다시 시도해주세요.");
    },
  });

  const startEdit = (holding: Holding) => {
    setEditId(holding.id);
    setEditForm({ quantity: holding.quantity, avg_price: holding.avg_price });
  };

  const cancelEdit = () => {
    setEditId(null);
  };

  const setEditFormField = (field: "quantity" | "avg_price", value: string) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  };

  const saveEdit = (holdingId: number) => {
    editHoldingMutation.mutate({
      holdingId,
      quantity: Number(editForm.quantity),
      avg_price: Number(editForm.avg_price),
    });
  };

  return {
    editId,
    editForm,
    isEditPending: editHoldingMutation.isPending,
    startEdit,
    cancelEdit,
    setEditFormField,
    saveEdit,
  };
}
