"use client";

import { PackageOpen, RefreshCw, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PnLBadge } from "@/components/PnLBadge";
import { PageError } from "@/components/PageError";
import { TableSkeleton } from "@/components/TableSkeleton";
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
import { formatKRW, formatNumber, formatPrice } from "@/lib/format";
import type { ExistingHolding } from "@/components/OrderDialog";

interface Holding {
  id: number;
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
  current_price: string | null;
  market_value: string | null;
  market_value_krw: string | null;
  pnl_amount: string | null;
  pnl_rate: string | null;
  exchange_rate: string | null;
  currency?: "KRW" | "USD";
}

interface AddForm {
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
}

function formatUSD(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const num = Number(value);
  if (isNaN(num)) return "—";
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface HoldingsSectionProps {
  holdings: Holding[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  onRetry: () => void;
  isKisConnected: boolean;
  isSyncing: boolean;
  onKisSync: () => void;
  onSearchOpen: () => void;
  // Add form
  addForm: AddForm | null;
  addFormErrors: { quantity?: string; avg_price?: string };
  addHoldingPending: boolean;
  onSetAddForm: (form: ((prev: AddForm | null) => AddForm | null) | AddForm | null) => void;
  onSetAddFormErrors: (errors: { quantity?: string; avg_price?: string }) => void;
  onHandleAdd: () => void;
  // Edit form
  editId: number | null;
  editForm: { quantity: string; avg_price: string };
  editHoldingPending: boolean;
  onSetEditId: (id: number | null) => void;
  onSetEditForm: (form: { quantity: string; avg_price: string }) => void;
  onEditSave: (id: number) => void;
  // Delete confirm
  deleteConfirmId: number | null;
  deleteHoldingPending: boolean;
  onSetDeleteConfirmId: (id: number | null) => void;
  onDeleteHolding: (id: number) => void;
  // Order dialog
  onOpenOrder: (
    ticker: string,
    name: string,
    currentPrice: number | undefined,
    tab: "BUY" | "SELL",
    exchangeCode: string | undefined,
    existingHolding: ExistingHolding | undefined
  ) => void;
}

export function HoldingsSection({
  holdings,
  isLoading,
  isError,
  error,
  onRetry,
  isKisConnected,
  isSyncing,
  onKisSync,
  onSearchOpen,
  addForm,
  addFormErrors,
  addHoldingPending,
  onSetAddForm,
  onSetAddFormErrors,
  onHandleAdd,
  editId,
  editForm,
  editHoldingPending,
  onSetEditId,
  onSetEditForm,
  onEditSave,
  deleteConfirmId,
  deleteHoldingPending,
  onSetDeleteConfirmId,
  onDeleteHolding,
  onOpenOrder,
}: HoldingsSectionProps): React.ReactElement {
  return (
    <>
      {isLoading ? (
        <TableSkeleton rows={4} columns={6} />
      ) : isError ? (
        <PageError
          message={
            error instanceof Error
              ? error.message
              : "보유 종목을 불러올 수 없습니다"
          }
          onRetry={onRetry}
        />
      ) : holdings.length === 0 && !addForm ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <PackageOpen className="mb-3 h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          {isKisConnected ? (
            <>
              <p className="font-medium">
                KIS 계좌가 연결됐지만 아직 동기화되지 않았습니다
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                실계좌 보유 종목을 불러오려면 동기화를 실행하세요.
              </p>
              <Button
                onClick={onKisSync}
                disabled={isSyncing}
                className="mt-4 gap-2"
              >
                <RefreshCw
                  className={`h-4 w-4 ${isSyncing ? "animate-spin" : ""}`}
                  aria-hidden="true"
                />
                {isSyncing ? "동기화 중..." : "지금 동기화"}
              </Button>
            </>
          ) : (
            <>
              <p className="font-medium">보유 종목이 없습니다</p>
              <p className="mt-1 text-sm text-muted-foreground">
                종목을 검색해서 추가해보세요.
              </p>
              <Button onClick={onSearchOpen} className="mt-4 gap-2">
                <Search className="h-4 w-4" aria-hidden="true" />
                종목 검색
              </Button>
            </>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                {[
                  "종목",
                  "수량",
                  "평균단가",
                  "현재가",
                  "손익 (KRW)",
                  "평가금액 (KRW)",
                  "",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left font-medium text-muted-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...holdings]
                .sort(
                  (a, b) =>
                    Number(b.market_value_krw ?? 0) -
                    Number(a.market_value_krw ?? 0)
                )
                .map((h) => {
                  const isUSD = h.currency === "USD";
                  return (
                    <tr key={h.id} className="border-t hover:bg-muted/20">
                      {editId === h.id ? (
                        <>
                          <td className="px-4 py-2">
                            <div className="font-medium">{h.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {h.ticker}
                            </div>
                          </td>
                          <td className="px-4 py-2">
                            <Input
                              type="number"
                              value={editForm.quantity}
                              onChange={(e) =>
                                onSetEditForm({
                                  ...editForm,
                                  quantity: e.target.value,
                                })
                              }
                              className="w-24 h-8"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <Input
                              type="number"
                              value={editForm.avg_price}
                              onChange={(e) =>
                                onSetEditForm({
                                  ...editForm,
                                  avg_price: e.target.value,
                                })
                              }
                              className="w-28 h-8"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => onEditSave(h.id)}
                                disabled={editHoldingPending}
                              >
                                저장
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => onSetEditId(null)}
                              >
                                취소
                              </Button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="px-4 py-3">
                            <div className="font-medium">{h.name}</div>
                            <div className="text-xs text-muted-foreground">
                              {h.ticker}
                              {isUSD && (
                                <span className="ml-1 rounded bg-blue-100 px-1 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                                  USD
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 tabular-nums">
                            {formatNumber(h.quantity)}
                          </td>
                          <td className="px-4 py-3 tabular-nums">
                            {isUSD
                              ? formatUSD(h.avg_price)
                              : formatPrice(h.avg_price, "KRW")}
                          </td>
                          <td className="px-4 py-3 tabular-nums">
                            {h.current_price ? (
                              <div>
                                <span>
                                  {isUSD
                                    ? formatUSD(h.current_price)
                                    : formatPrice(h.current_price, "KRW")}
                                </span>
                                {isUSD && h.exchange_rate && (
                                  <div className="text-xs text-muted-foreground">
                                    ≈{" "}
                                    {formatKRW(
                                      String(
                                        Number(h.current_price) *
                                          Number(h.exchange_rate)
                                      )
                                    )}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {h.pnl_amount != null ? (
                              <div>
                                <PnLBadge value={h.pnl_amount} />
                                {h.pnl_rate != null && (
                                  <div className="text-xs text-muted-foreground">
                                    {Number(h.pnl_rate) >= 0 ? "+" : ""}
                                    {Number(h.pnl_rate).toFixed(2)}%
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 tabular-nums">
                            {h.market_value_krw != null ? (
                              <div>
                                <span>{formatKRW(h.market_value_krw)}</span>
                                {isUSD && h.market_value != null && (
                                  <div className="text-xs text-muted-foreground">
                                    {formatUSD(h.market_value)}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1 flex-wrap">
                              {isKisConnected && (
                                <>
                                  <button
                                    onClick={() =>
                                      onOpenOrder(
                                        h.ticker,
                                        h.name,
                                        h.current_price
                                          ? Number(h.current_price)
                                          : undefined,
                                        "BUY",
                                        h.currency === "USD"
                                          ? h.ticker.includes(".")
                                            ? h.ticker.split(".")[1]
                                            : "NASD"
                                          : undefined,
                                        {
                                          quantity: h.quantity,
                                          avg_price: h.avg_price,
                                          pnl_amount: h.pnl_amount,
                                          pnl_rate: h.pnl_rate,
                                        }
                                      )
                                    }
                                    className="rounded border px-2 py-0.5 text-xs font-medium text-red-600 border-red-200 hover:bg-red-50"
                                  >
                                    매수
                                  </button>
                                  <button
                                    onClick={() =>
                                      onOpenOrder(
                                        h.ticker,
                                        h.name,
                                        h.current_price
                                          ? Number(h.current_price)
                                          : undefined,
                                        "SELL",
                                        h.currency === "USD"
                                          ? h.ticker.includes(".")
                                            ? h.ticker.split(".")[1]
                                            : "NASD"
                                          : undefined,
                                        {
                                          quantity: h.quantity,
                                          avg_price: h.avg_price,
                                          pnl_amount: h.pnl_amount,
                                          pnl_rate: h.pnl_rate,
                                        }
                                      )
                                    }
                                    className="rounded border px-2 py-0.5 text-xs font-medium text-blue-600 border-blue-200 hover:bg-blue-50"
                                  >
                                    매도
                                  </button>
                                </>
                              )}
                              <button
                                onClick={() => {
                                  onSetEditId(h.id);
                                  onSetEditForm({
                                    quantity: h.quantity,
                                    avg_price: h.avg_price,
                                  });
                                }}
                                className="rounded border px-3 py-1 text-xs hover:bg-muted"
                              >
                                수정
                              </button>
                              <button
                                onClick={() => onSetDeleteConfirmId(h.id)}
                                className="rounded border px-3 py-1 text-xs text-destructive hover:bg-destructive/10"
                                aria-label={`${h.name} 삭제`}
                              >
                                <Trash2 className="h-3 w-3" aria-hidden="true" />
                              </button>
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                  );
                })}

              {/* 종목 추가 폼 행 */}
              {addForm && (
                <tr className="border-t bg-muted/10">
                  <td className="px-4 py-2">
                    <div className="font-medium">{addForm.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {addForm.ticker}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col gap-1">
                      <input
                        type="number"
                        placeholder="수량"
                        value={addForm.quantity}
                        onChange={(e) => {
                          onSetAddForm((f) =>
                            f ? { ...f, quantity: e.target.value } : f
                          );
                          onSetAddFormErrors({
                            ...addFormErrors,
                            quantity: undefined,
                          });
                        }}
                        className="w-24 h-8"
                        aria-invalid={!!addFormErrors.quantity}
                      />
                      {addFormErrors.quantity && (
                        <span className="text-[10px] text-destructive">
                          {addFormErrors.quantity}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col gap-1">
                      <input
                        type="number"
                        placeholder="평균단가"
                        value={addForm.avg_price}
                        onChange={(e) => {
                          onSetAddForm((f) =>
                            f ? { ...f, avg_price: e.target.value } : f
                          );
                          onSetAddFormErrors({
                            ...addFormErrors,
                            avg_price: undefined,
                          });
                        }}
                        className="w-28 h-8"
                        aria-invalid={!!addFormErrors.avg_price}
                      />
                      {addFormErrors.avg_price && (
                        <span className="text-[10px] text-destructive">
                          {addFormErrors.avg_price}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={onHandleAdd}
                        disabled={
                          addHoldingPending ||
                          !addForm.quantity ||
                          !addForm.avg_price
                        }
                      >
                        추가
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          onSetAddForm(null);
                          onSetAddFormErrors({});
                        }}
                      >
                        취소
                      </Button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 보유종목 삭제 확인 — shadcn AlertDialog */}
      <AlertDialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => {
          if (!open) onSetDeleteConfirmId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>종목을 삭제하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              이 작업은 되돌릴 수 없습니다. 관련 거래내역도 모두 삭제됩니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteConfirmId !== null) {
                  onDeleteHolding(deleteConfirmId);
                }
              }}
            >
              {deleteHoldingPending ? "삭제 중..." : "삭제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
