# THE WEALTH — 주식 매매(Trading) 기능 구현 프롬프트

## 개요

The Wealth 프로젝트에 **실제 주식 매매(Buy/Sell) 기능**을 추가합니다. 현재 시스템은 거래내역을 수동으로 기록하는 방식이지만, 이번 작업에서는 KIS OpenAPI를 통해 **실제 주문을 실행**하고, 포트폴리오 내에서 **총 평가금액과 예수금(현금 잔고)**을 실시간으로 표시하며, **신규 종목 매수 및 기존 보유 종목의 추가 매수/매도**를 포트폴리오 화면 안에서 수행할 수 있도록 합니다.

대상 계좌 유형: **ISA 계좌, 일반 주식 계좌, 해외 주식 계좌, 연금저축 계좌** 모두 지원해야 합니다.

---

## 현재 시스템 분석 (컨텍스트)

### 기존 아키텍처
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 + Redis 7
- **Frontend**: Next.js 16 + React 19 + TanStack Query + Zustand + shadcn/ui + Tailwind v4
- **KIS 연동**: 현재가 조회(`FHKST01010100`), 해외 현재가(`HHDFS00000300`), 잔고 조회, 체결내역 조회(`TTTC8001R`, `TTTS3035R`)까지 구현됨
- **계좌 관리**: `kis_accounts` 테이블에 app_key/app_secret을 AES-256-GCM으로 암호화 저장, 포트폴리오와 1:1 매핑
- **거래내역**: `transactions` 테이블에 BUY/SELL 기록이 수동으로 저장되고 보유종목 수량에 반영됨
- **대시보드**: 30초 폴링 + SSE 실시간 가격 스트리밍, 총 자산/수익률 표시

### 현재 없는 것 (이번에 구현할 것)
- KIS API를 통한 **실제 주문 실행** (매수/매도 API 호출)
- 포트폴리오 화면에서의 **예수금(현금 잔고)** 표시
- 포트폴리오 내에서 직접 **매매 주문 UI** (신규 종목 매수, 기존 종목 추가 매수/매도)
- **계좌 유형별** 주문 분기 처리 (ISA, 연금저축, 해외주식 등)
- 주문 상태 조회 및 주문 체결 후 자동 동기화

---

## Phase 1: 백엔드 — KIS 주문 API 연동

### 1-1. KIS 주문 서비스 생성

**파일**: `backend/app/services/kis_order.py`

KIS OpenAPI 주문 관련 TR_ID 정리:

| 구분 | 매수 TR_ID | 매도 TR_ID | API Path |
|------|-----------|-----------|----------|
| **국내주식 (일반/ISA)** | `TTTC0802U` | `TTTC0801U` | `/uapi/domestic-stock/v1/trading/order-cash` |
| **국내주식 (연금저축/IRP)** | `TTTC0852U` | `TTTC0851U` | `/uapi/domestic-stock/v1/trading/order-cash` (연금 전용 TR) |
| **해외주식 (미국)** | `JTTT1002U` | `JTTT1006U` | `/uapi/overseas-stock/v1/trading/order` |
| **해외주식 (기타)** | 거래소별 TR_ID 상이 | 거래소별 TR_ID 상이 | `/uapi/overseas-stock/v1/trading/order` |

> **주의**: KIS API는 모의투자/실전투자 환경에 따라 TR_ID가 달라집니다. 실전투자 기준으로 구현하되, 환경 설정으로 분기 가능하도록 합니다. `kis_accounts` 테이블에 `is_paper_trading` (Boolean, default: false) 컬럼을 추가하여 모의투자/실전투자를 구분합니다.

구현할 함수:

```python
# 국내주식 현금 주문
async def place_domestic_order(
    kis_account: KisAccount,
    ticker: str,
    order_type: Literal["BUY", "SELL"],
    quantity: int,
    price: Decimal,  # 0이면 시장가
    order_class: Literal["지정가", "시장가", "조건부지정가", "최유리지정가", "최우선지정가"] = "지정가",
) -> OrderResult:
    """
    국내주식 매수/매도 주문
    - 계좌 상품코드(acnt_prdt_cd)로 일반/ISA/연금 구분
    - ISA: 동일한 TR_ID 사용 가능, 계좌번호로 구분
    - 연금저축/IRP: 전용 TR_ID(TTTC0852U/TTTC0851U) 사용
    """

# 해외주식 주문
async def place_overseas_order(
    kis_account: KisAccount,
    ticker: str,
    exchange: Literal["NYSE", "NASDAQ", "AMEX", "HKEX", "TSE", "SHE", "SSE"],
    order_type: Literal["BUY", "SELL"],
    quantity: int,
    price: Decimal,
    order_class: Literal["지정가", "시장가"] = "지정가",
) -> OrderResult:
    """해외주식 매수/매도 (거래소별 TR_ID 분기)"""

# 주문 가능 수량/금액 조회
async def get_orderable_quantity(
    kis_account: KisAccount,
    ticker: str,
    price: Decimal,
    order_type: Literal["BUY", "SELL"],
) -> OrderableInfo:
    """
    - 매수: 예수금 기반 최대 매수 가능 수량 계산
    - 매도: 보유 수량 조회
    - 국내: TTTC8908R (매수가능조회)
    - 해외: TTTS3007R (매수가능금액조회)
    """

# 주문 내역(미체결) 조회
async def get_pending_orders(
    kis_account: KisAccount,
) -> list[PendingOrder]:
    """
    미체결 주문 목록 조회
    - 국내: TTTC8036R
    - 해외: JTTT3018R
    """

# 주문 취소/정정
async def cancel_order(
    kis_account: KisAccount,
    order_no: str,
    ticker: str,
    quantity: int,
    is_overseas: bool = False,
) -> CancelResult:
    """
    미체결 주문 취소
    - 국내: TTTC0803U
    - 해외: JTTT1004U
    """
```

### 1-2. 예수금(현금 잔고) 조회 서비스

**파일**: `backend/app/services/kis_balance.py` (기존 `kis_account.py` 확장 또는 별도)

```python
async def get_cash_balance(
    kis_account: KisAccount,
) -> CashBalanceInfo:
    """
    계좌 예수금 조회
    - 국내: TTTC8434R (예수금상세조회)
      → 응답 필드: dnca_tot_amt (예수금총액), prvs_rcdl_excc_amt (가용 예수금)
    - 해외: TTTS3012R (해외주식 체결기준잔고)
      → 응답 필드: frcr_pchs_amt (외화매수금액), us_tot_hldg_pfls (미국 총 보유 손익)
    
    반환값:
    - total_cash: 총 예수금 (원화 기준)
    - available_cash: 주문 가능 금액
    - currency: KRW/USD
    - foreign_cash: 외화 예수금 (해외계좌인 경우)
    """
```

### 1-3. Pydantic 스키마 정의

**파일**: `backend/app/schemas/order.py`

```python
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Literal, Optional

class OrderRequest(BaseModel):
    ticker: str
    order_type: Literal["BUY", "SELL"]
    quantity: int
    price: Decimal  # 0이면 시장가
    order_class: str = "지정가"
    memo: Optional[str] = None  # 거래 메모 (투자 일지)

class OrderResult(BaseModel):
    success: bool
    order_no: Optional[str] = None  # KIS 주문번호
    message: str
    ordered_at: datetime

class OrderableInfoResponse(BaseModel):
    max_quantity: int  # 최대 주문 가능 수량
    available_cash: Decimal  # 가용 예수금
    current_price: Decimal  # 현재가 (참고용)
    currency: str

class CashBalanceResponse(BaseModel):
    total_cash: Decimal  # 총 예수금
    available_cash: Decimal  # 주문 가능 금액
    total_evaluation: Decimal  # 총 평가금액
    total_profit_loss: Decimal  # 총 평가손익
    profit_loss_rate: Decimal  # 총 수익률 (%)
    currency: str
    foreign_cash: Optional[Decimal] = None  # 외화 예수금
    usd_krw_rate: Optional[Decimal] = None  # 환율

class PendingOrderResponse(BaseModel):
    order_no: str
    ticker: str
    name: str
    order_type: Literal["BUY", "SELL"]
    quantity: int
    price: Decimal
    filled_quantity: int
    status: str  # 접수, 체결, 부분체결, 거부
    ordered_at: datetime
```

### 1-4. API 엔드포인트

**파일**: `backend/app/api/orders.py` (새 라우터)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/portfolios/{id}/orders` | 매수/매도 주문 실행 |
| `GET` | `/portfolios/{id}/orders/orderable` | 주문 가능 수량/금액 조회 (query: `ticker`, `price`, `order_type`) |
| `GET` | `/portfolios/{id}/orders/pending` | 미체결 주문 목록 |
| `DELETE` | `/portfolios/{id}/orders/{order_no}` | 주문 취소 |
| `GET` | `/portfolios/{id}/cash-balance` | 예수금 및 총 평가금액 조회 |

핵심 로직:
1. 주문 실행(`POST /orders`) 시:
   - KIS API로 실제 주문 전송
   - 성공하면 `transactions` 테이블에 자동 기록 (type=BUY/SELL, 주문번호 포함)
   - `holdings` 테이블의 수량/평균단가 자동 업데이트
   - 실패하면 에러 메시지 반환 (예수금 부족, 장 종료, 종목 정지 등)
2. 예수금 조회(`GET /cash-balance`) 시:
   - KIS API 예수금 + 총 평가금액을 한 번에 조회
   - Redis 캐시 (TTL: 30초) 적용
3. 주문 가능 수량(`GET /orderable`) 시:
   - 매수: 예수금 ÷ 주문가격 = 최대 수량
   - 매도: 보유 수량 반환

### 1-5. DB 스키마 변경

**Alembic migration 필요:**

```python
# kis_accounts 테이블에 추가
is_paper_trading = Column(Boolean, default=False, nullable=False)
account_type = Column(String(20), nullable=True)  # "일반", "ISA", "연금저축", "IRP", "해외"

# transactions 테이블에 추가
order_no = Column(String(50), nullable=True)  # KIS 주문번호 (수동 입력은 null)
order_source = Column(String(10), default="manual")  # "manual" | "api" (주문 출처 구분)

# orders 테이블 (새로 생성 - 주문 이력 추적용)
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    kis_account_id = Column(Integer, ForeignKey("kis_accounts.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    order_type = Column(String(4), nullable=False)  # BUY/SELL
    order_class = Column(String(20), nullable=False)  # 지정가/시장가
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric, nullable=False)
    order_no = Column(String(50), nullable=True)  # KIS 주문번호
    status = Column(String(20), default="pending")  # pending/filled/partial/cancelled/rejected
    filled_quantity = Column(Integer, default=0)
    filled_price = Column(Numeric, nullable=True)  # 체결 평균가
    memo = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 1-6. 안전장치 및 에러 처리

반드시 구현할 안전장치:

1. **이중 주문 방지**: Redis 기반 주문 락 (`order_lock:{portfolio_id}:{ticker}`, TTL: 10초)
2. **장 운영시간 체크**: 국내 09:00~15:30, 해외 시장별 다름 — 장외 시간 주문 시 명확한 안내 메시지
3. **주문 금액 상한**: 1회 주문 금액 상한 설정 가능 (설정 페이지에서 관리)
4. **주문 확인 단계**: 프론트엔드에서 주문 전 확인 다이얼로그 필수
5. **에러 분류**: KIS API 에러 코드별 사용자 친화적 메시지 매핑
6. **레이트 리밋**: 주문 API에 별도 레이트 리밋 (5회/분)
7. **감사 로그**: 모든 주문 시도를 `orders` 테이블에 기록 (성공/실패 모두)

---

## Phase 2: 프론트엔드 — 포트폴리오 내 매매 UI

### 2-1. 포트폴리오 상세 페이지 개편

**파일**: `frontend/src/app/dashboard/portfolios/[id]/page.tsx` 개편

현재 포트폴리오 상세 페이지에 다음을 추가:

#### 상단 요약 영역 (항상 표시)

```
┌──────────────────────────────────────────────────────┐
│  📊 내 ISA 계좌                                       │
│                                                       │
│  총 평가금액        예수금(현금)       총 수익률         │
│  ₩15,234,500      ₩2,340,000       +12.3%           │
│  ▲ ₩1,678,000     (주문 가능)        (+₩1,678,000)   │
│                                                       │
│  [신규 종목 매수]  [전체 동기화]  [미체결 주문 (2)]     │
└──────────────────────────────────────────────────────┘
```

- **총 평가금액**: KIS 잔고 API에서 조회한 총 평가금액 (보유주식 시가평가 + 예수금)
- **예수금**: 주문 가능한 현금 잔고
- **총 수익률**: (총 평가금액 - 총 매입금액) / 총 매입금액 × 100
- 30초 폴링으로 자동 갱신 (TanStack Query `refetchInterval`)
- KIS 연결 안 된 포트폴리오는 예수금 영역 숨기고 기존 UI 유지

#### 보유종목 테이블에 매매 버튼 추가

기존 `HoldingsTable.tsx`에 각 종목 행 우측에 **[매수]** **[매도]** 버튼 추가:

```
┌────────┬──────┬────────┬────────┬──────┬──────────┬─────────────┐
│ 종목명  │ 수량 │ 평균가  │ 현재가  │수익률 │ 수익/손실  │   액션       │
├────────┼──────┼────────┼────────┼──────┼──────────┼─────────────┤
│삼성전자 │ 100  │ 60,000 │ 68,000 │+13.3%│ +800,000 │ [매수][매도] │
│SK하이닉 │  50  │120,000 │ 95,000 │-20.8%│-1,250,000│ [매수][매도] │
└────────┴──────┴────────┴────────┴──────┴──────────┴─────────────┘
```

- KIS 계좌 연결된 포트폴리오에서만 매수/매도 버튼 표시
- 연결 안 된 경우 기존 수동 거래 기록 UI 유지

### 2-2. 주문 다이얼로그 컴포넌트

**파일**: `frontend/src/components/OrderDialog.tsx` (신규)

shadcn/ui `Dialog` + `Tabs` 기반 주문 폼:

```
┌──────────────────────────────────────┐
│  삼성전자 (005930)        ✕ 닫기     │
│  현재가: ₩68,000  ▲2.3%              │
├──────────────────────────────────────┤
│  [매수]  [매도]            ← Tabs    │
├──────────────────────────────────────┤
│                                      │
│  주문유형:  ○ 지정가  ● 시장가        │
│                                      │
│  주문가격:  [  68,000  ] 원          │
│            (시장가 선택시 비활성화)     │
│                                      │
│  주문수량:  [    10    ] 주          │
│            [10%][25%][50%][100%]     │
│            주문 가능: 34주            │
│                                      │
│  주문금액:  ₩680,000                 │
│  예수금:    ₩2,340,000               │
│  수수료(약): ₩150                    │
│                                      │
│  메모: [투자 근거를 입력하세요...]     │
│                                      │
│  ┌──────────────────────────────┐   │
│  │     매수 주문 실행             │   │
│  └──────────────────────────────┘   │
│                                      │
│  ⚠ 투자에 따른 책임은 본인에게        │
│    있습니다.                          │
└──────────────────────────────────────┘
```

주요 기능:
- **주문 유형 선택**: 지정가 / 시장가 (추후 조건부지정가, 최유리지정가 등 확장 가능)
- **수량 퀵 버튼**: 예수금 기준 10% / 25% / 50% / 100% 수량 자동 계산
- **실시간 주문금액 계산**: 수량 × 가격 실시간 표시
- **주문 가능 수량 표시**: API에서 조회한 최대 주문 가능 수량
- **메모 필드**: 투자 일지용 거래 메모 (기존 `transactions.memo`와 연계)
- **확인 단계**: 주문 버튼 클릭 → 확인 다이얼로그 → 최종 실행
- 매수=빨간색 버튼, 매도=파란색 버튼 (한국 증시 컬러 컨벤션)

### 2-3. 신규 종목 매수 플로우

**포트폴리오 상세 페이지의 "신규 종목 매수" 버튼 클릭 시:**

1. `StockSearchDialog` (Cmd+K 검색)과 유사한 종목 검색 UI 표시
2. 종목 선택 시 → `OrderDialog` 자동 열림 (매수 탭 활성)
3. 주문 실행 성공 시:
   - `holdings` 테이블에 신규 종목 자동 추가
   - `transactions` 테이블에 거래 기록
   - `orders` 테이블에 주문 이력 기록
   - TanStack Query 캐시 무효화 → 보유종목 테이블 즉시 갱신

### 2-4. 미체결 주문 패널

**파일**: `frontend/src/components/PendingOrdersPanel.tsx` (신규)

포트폴리오 상세 페이지 내 탭 또는 접이식 패널로 미체결 주문 표시:

```
┌──────────────────────────────────────────────────┐
│  미체결 주문 (2건)                         [새로고침] │
├──────────────────────────────────────────────────┤
│  삼성전자  매수  10주 × ₩67,500   대기중  [취소]  │
│  카카오    매도   5주 × ₩43,000   대기중  [취소]  │
└──────────────────────────────────────────────────┘
```

- 30초 폴링으로 미체결 상태 자동 갱신
- 체결 완료 시 목록에서 제거 + sonner toast 알림
- 주문 취소 기능

### 2-5. TanStack Query 훅

**파일**: `frontend/src/hooks/useOrders.ts` (신규)

```typescript
// 예수금 & 총평가 조회
export function useCashBalance(portfolioId: number) {
  return useQuery({
    queryKey: ['cash-balance', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/cash-balance`),
    refetchInterval: 30_000,
    enabled: !!portfolioId,
  });
}

// 주문 가능 수량 조회
export function useOrderableQuantity(portfolioId: number, ticker: string, price: number, orderType: string) {
  return useQuery({
    queryKey: ['orderable', portfolioId, ticker, price, orderType],
    queryFn: () => api.get(`/portfolios/${portfolioId}/orders/orderable`, { params: { ticker, price, order_type: orderType } }),
    enabled: !!ticker && price > 0,
  });
}

// 주문 실행 mutation
export function usePlaceOrder(portfolioId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (order: OrderRequest) => api.post(`/portfolios/${portfolioId}/orders`, order),
    onSuccess: () => {
      // 관련 캐시 모두 무효화
      queryClient.invalidateQueries({ queryKey: ['cash-balance', portfolioId] });
      queryClient.invalidateQueries({ queryKey: ['holdings', portfolioId] });
      queryClient.invalidateQueries({ queryKey: ['transactions', portfolioId] });
      queryClient.invalidateQueries({ queryKey: ['pending-orders', portfolioId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// 미체결 주문 조회
export function usePendingOrders(portfolioId: number) {
  return useQuery({
    queryKey: ['pending-orders', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/orders/pending`),
    refetchInterval: 30_000,
  });
}

// 주문 취소 mutation
export function useCancelOrder(portfolioId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderNo, ticker, quantity }: CancelRequest) =>
      api.delete(`/portfolios/${portfolioId}/orders/${orderNo}`, { params: { ticker, quantity } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-orders', portfolioId] });
      queryClient.invalidateQueries({ queryKey: ['cash-balance', portfolioId] });
    },
  });
}
```

---

## Phase 3: 대시보드 통합

### 3-1. 대시보드 요약에 예수금 표시

**파일**: `backend/app/api/dashboard.py` 수정, `frontend/src/app/dashboard/page.tsx` 수정

`GET /dashboard/summary` 응답에 추가:

```json
{
  "portfolios": [...],
  "total_evaluation": 45230000,
  "total_cash": 5340000,
  "total_assets": 50570000,
  "total_profit_loss": 3200000,
  "total_profit_loss_rate": 7.65,
  "kis_status": "ok"
}
```

- `total_evaluation`: 모든 포트폴리오의 보유주식 평가금액 합계
- `total_cash`: 모든 KIS 연결 계좌의 예수금 합계
- `total_assets`: total_evaluation + total_cash
- 프론트엔드 대시보드 상단에 총 자산(평가+예수금) 표시

### 3-2. 포트폴리오 목록 페이지 개편

**파일**: `frontend/src/app/dashboard/portfolios/page.tsx` 수정

각 포트폴리오 카드에 예수금 표시 추가:

```
┌──────────────────────────────────┐
│  📊 ISA 계좌                      │
│  총 평가: ₩15,234,500            │
│  예수금:  ₩2,340,000             │
│  수익률:  +12.3%                  │
│  [상세보기]                       │
└──────────────────────────────────┘
```

---

## Phase 4: 계좌 유형별 처리

### 4-1. kis_accounts 테이블 확장

```python
account_type = Column(String(20), nullable=True)
# 값: "일반", "ISA", "연금저축", "IRP", "해외주식"
# KIS 계좌 등록/수정 시 사용자가 선택
```

### 4-2. 계좌 유형별 주문 분기

| 계좌 유형 | 국내 매수 TR | 국내 매도 TR | 해외 가능 | 비고 |
|----------|------------|------------|----------|------|
| 일반 | TTTC0802U | TTTC0801U | ✅ | 기본 |
| ISA | TTTC0802U | TTTC0801U | ❌ | 국내만 가능, 동일 TR 사용 |
| 연금저축 | TTTC0852U | TTTC0851U | ❌ | 전용 TR_ID |
| IRP | TTTC0852U | TTTC0851U | ❌ | 전용 TR_ID |
| 해외주식 | TTTC0802U | TTTC0801U | ✅ | 해외 전용 계좌도 국내 매매 가능 |

### 4-3. 설정 페이지 확장

**파일**: `frontend/src/app/dashboard/settings/page.tsx` 수정

KIS 계좌 관리에서:
- 계좌 유형 선택 드롭다운 추가 (일반/ISA/연금저축/IRP/해외주식)
- 모의투자/실전투자 토글 추가
- 1회 주문 금액 상한 설정 입력 필드 추가

---

## 구현 순서

```
Step 1: DB 마이그레이션
  - kis_accounts에 is_paper_trading, account_type 추가
  - transactions에 order_no, order_source 추가
  - orders 테이블 생성
  → alembic revision --autogenerate -m "add_trading_support"

Step 2: 백엔드 서비스 계층
  - kis_order.py (주문 실행/취소)
  - kis_balance.py 확장 (예수금 조회)
  - schemas/order.py (Pydantic 스키마)

Step 3: 백엔드 API 계층
  - api/orders.py (라우터 등록)
  - main.py에 라우터 추가
  - dashboard.py에 예수금 필드 추가

Step 4: 백엔드 테스트
  - tests/test_orders.py
  - KIS API mock으로 주문 플로우 테스트
  - 이중 주문 방지 테스트
  - 계좌 유형별 TR_ID 분기 테스트

Step 5: 프론트엔드 훅 & API
  - hooks/useOrders.ts
  - types에 Order 관련 타입 추가

Step 6: 프론트엔드 UI
  - OrderDialog.tsx (주문 다이얼로그)
  - PendingOrdersPanel.tsx (미체결 주문)
  - 포트폴리오 상세 페이지 개편
  - HoldingsTable에 매수/매도 버튼 추가
  - 대시보드 요약에 예수금 표시

Step 7: 설정 페이지 확장
  - 계좌 유형 선택
  - 모의투자/실전투자 토글
  - 주문 금액 상한 설정

Step 8: E2E 테스트
  - 주문 플로우 E2E (Playwright)
  - 에러 케이스 (예수금 부족, 장외 시간 등)
```

---

## 주의사항

1. **KIS API 레이트 리밋**: 주문 API도 초당 1~2건 제한. 연속 주문 시 딜레이 필요
2. **실전투자 위험**: 실제 돈이 오가므로 반드시 모의투자 환경에서 충분히 테스트 후 실전 전환
3. **장 운영시간**: 국내 09:00~15:30, 해외는 시장별 상이. 장외 시간 주문 가능 여부 KIS 문서 확인 필요
4. **예수금 캐싱**: 예수금은 주문 직후 변동되므로 주문 성공 시 캐시 즉시 무효화
5. **동시성 처리**: 같은 종목에 대한 동시 주문 방지 (Redis 분산 락)
6. **계좌 상품코드**: `acnt_prdt_cd`로 계좌 유형 자동 감지가 가능한지 KIS 문서 확인. 불가하면 사용자 수동 입력
7. **해외주식 환율**: 해외 매매 시 환전 필요. KIS API의 환전 관련 파라미터 확인 필요
8. **기존 호환성 유지**: KIS 미연결 포트폴리오는 기존 수동 거래기록 방식 유지. 매매 버튼 숨김 처리
