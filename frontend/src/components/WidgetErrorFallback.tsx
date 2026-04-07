"use client";

/**
 * WidgetErrorFallback — 인라인 위젯 오류 상태 컴포넌트.
 *
 * 대시보드·분석 페이지의 섹션 단위 로드 실패 시 표시된다.
 * ErrorBoundary의 전체화면 fallback과 달리 카드 내부에 맞는 작은 크기로 설계됐다.
 */

interface WidgetErrorFallbackProps {
  /** 사용자에게 표시할 오류 메시지 */
  message?: string;
  /** 재시도 버튼 클릭 핸들러 */
  onRetry?: () => void;
}

export function WidgetErrorFallback({
  message = "데이터를 불러오지 못했습니다.",
  onRetry,
}: WidgetErrorFallbackProps) {
  return (
    <div className="flex items-center gap-2 text-sm text-destructive">
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
