# Annual Returns Feature

연도별 수익률 트래킹 + 은퇴 시뮬레이션 메뉴.

요청 배경: 사용자가 종목 단위 수익이 아닌 **"1년마다 얼마나 벌고 있는지"** 만 빠르게
확인하고 싶음. 참고 시트 2개:
- `1h3_0IeY3C-fayV6nbzP38CPY4K-xTwnWBw_FvlbE_Cc` — 현재 보유 종목 평가 (앱이 이미 제공)
- `1u0Z_TS51nIK2gg86fGAtl5igdHG_UurmON7ZgyuJxWc` — 나이 × 연도 × 적립 × 수익률 × 총금액 (32~100세)

---

## 1. 스코프

| 항목 | 포함 | 비고 |
|------|------|------|
| 과거 연도별 IRR/평가/적립 표 | ✅ | transactions + price_snapshots + dividends 집계 |
| 과거 평가액·적립 라인+바 차트 | ✅ | Recharts ComposedChart |
| 미래 은퇴 시뮬레이션 표·차트 | ✅ | 입력값 기반 순계산, DB 무관 |
| 시뮬레이션 파라미터 저장 | ✅ | `users.simulation_params JSONB` |
| 사용자 생년 입력 | ✅ | `users.birth_year SMALLINT NULL` |
| 종목별 연간 수익 breakdown | ❌ | 본 메뉴 범위 밖. analytics 페이지에서 이미 종목별 P&L 제공 |
| TWR 계산 | ❌ | MWR/IRR 만 채택 (사용자 결정) |

---

## 2. 백엔드 설계

### 2.1 IRR 계산 유틸 — `app/services/irr_utils.py` (신규)

```python
def xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float | None:
    """불규칙 일자 현금흐름의 연복리 IRR.
    cashflows: [(date, amount)], 음수=유입(매입/배당수취 전 입금), 양수=유출(매도/배당)
    반환: 연 IRR (예: 0.0774 → 7.74%). 해 없으면 None.
    """
```

- 구현: `scipy.optimize.brentq` 로 `sum(cf / (1+r)^days_diff) = 0` 의 해를 찾는다.
  scipy 가 무거우면 numpy + 이분법 직접 구현 (의존성 검토는 TASK 단계에서).
- 부호 컨벤션: **투자자 관점에서 음수=유출(매수/적립), 양수=유입(매도/배당/평가종료)**.

### 2.2 `GET /analytics/annual-returns`

응답 스키마:
```ts
type AnnualReturn = {
  year: number;
  age: number | null;            // users.birth_year 있을 때만
  bop_value_krw: number;         // 전년 말 평가액 (첫 해는 0)
  contributions_krw: number;     // 해당 연도 순 매입 (BUY - SELL)
  dividends_krw: number;         // 해당 연도 수령 배당 합계
  eop_value_krw: number;         // 연말 평가액 (12/31 직전 거래일)
  pnl_amount_krw: number;        // = eop - bop - contributions + (dividends already in eop?)
  irr_year: number | null;       // 해당 연도 1년 IRR (XIRR)
  irr_cumulative: number | null; // 최초 매수일 ~ 해당 연도 12/31 누적 XIRR
};
```

처리 순서:
1. 사용자의 모든 portfolio → 모든 transaction 조회 (`deleted_at IS NULL`).
2. 외화 거래는 `traded_at` 의 환율로 KRW 환산 (`fx_utils.forward_fill_rates` 재사용).
3. 보유 ticker 의 price_snapshot 중 각 연말 (12/31 또는 직전 영업일) 종가로 EOP value 산출.
4. 해당 연도 cashflow + EOP 평가액으로 XIRR (연간).
5. 첫 매수일부터 누적 cashflow + EOP 평가액으로 XIRR (누적).
6. `dividends` 테이블에서 `payment_date` 기준 연간 합계.
7. ETag + Redis 캐시 (key: `analytics:{user_id}:annual-returns`, TTL = `ANALYTICS_CACHE_TTL`).

엣지케이스:
- 거래내역 0건 → `[]` 반환.
- 연중 첫 매수 → 해당 연도 `bop_value_krw=0`, `irr_year` 정상 계산.
- IRR 수렴 실패 → `irr_year=null`, 표에서 "—" 표시.

### 2.3 `POST /analytics/retirement-simulation`

요청:
```ts
type SimulationInput = {
  current_value_krw: number;           // 시작 평가액 (기본: 현재 total_asset)
  current_age: number;                 // 시작 나이
  retirement_age: number;              // 인출 시작 나이
  end_age: number;                     // 시뮬레이션 종료 나이 (예: 100)
  annual_contribution_krw: number;     // 은퇴 전 연 적립
  annual_withdrawal_krw: number;       // 은퇴 후 연 인출 (양수 입력)
  expected_return_rate: number;        // 가정 수익률 (0.07 = 7%)
};
```

응답:
```ts
type SimulationPoint = {
  age: number;
  year: number;
  flow_krw: number;              // +적립 / -인출
  return_amount_krw: number;     // bop * rate
  eop_value_krw: number;
};
```

로직: 매년 `eop = bop * (1 + rate) + flow`. 순계산, DB 무관, 캐시 무관.
입력 검증은 Pydantic + `min/max` constraint.

### 2.4 `GET/PUT /users/me/simulation-params`

`users.simulation_params JSONB NULL` 컬럼에 마지막 입력값 저장. 다음 방문 시 폼 prefill.
스키마는 위 `SimulationInput` 과 동일.

### 2.5 DB 변경 — Alembic migration

```sql
ALTER TABLE users
  ADD COLUMN birth_year SMALLINT NULL,
  ADD COLUMN simulation_params JSONB NULL;
```

- `birth_year` 는 NULL 허용 (기존 사용자 영향 없음, 입력 시에만 나이 표시).
- 리버서블 (downgrade에서 DROP COLUMN).

---

## 3. 프론트엔드 설계

### 3.1 라우트 / 진입점
- 새 페이지: `/dashboard/annual-returns/page.tsx`
- 진입점:
  - `/dashboard/settings` 에 "연간 수익률 / 은퇴 시뮬레이션" 링크 추가
  - `/dashboard/analytics` 상단에 "연간 수익률 보기 →" 링크 카드
- BottomNav 슬롯은 그대로 유지 (홈 · 종목 · 포트폴리오 · 내정보).

### 3.2 페이지 구성

```
[요약 카드 4개]
누적 IRR | 총 적립액 | 현재 평가액 | 누적 평가차익

[과거 연도별 표] (TanStack Table)
연도 | 나이 | 연초 평가 | 적립 | 배당 | 연말 평가 | 연간수익 | IRR | 누적 IRR

[과거 차트] (Recharts ComposedChart)
X: 연도, 좌Y: 평가액 라인, 우Y: 연간 적립 바

[ 은퇴 시뮬레이션 ]

[입력 폼]
- 현재 평가액 (현재값 자동 prefill, 수정 가능)
- 현재 나이 / 은퇴 나이 / 종료 나이
- 연 적립액 / 연 인출액 / 가정 수익률(%)
- [시뮬레이션 실행] 버튼  [입력값 저장]

[시뮬레이션 결과 표]
나이 | 연도 | 적립/인출 | 운용수익 | 연말 평가액

[시뮬레이션 결과 차트] (Recharts AreaChart)
X: 나이, Y: 연말 평가액. 은퇴 나이에 ReferenceLine.
```

### 3.3 컴포넌트 분할
- `app/dashboard/annual-returns/page.tsx` — 페이지 entry
- `app/dashboard/annual-returns/AnnualSummaryCards.tsx`
- `app/dashboard/annual-returns/AnnualReturnsTable.tsx`
- `app/dashboard/annual-returns/AnnualReturnsChart.tsx`
- `app/dashboard/annual-returns/SimulationForm.tsx`
- `app/dashboard/annual-returns/SimulationResultTable.tsx`
- `app/dashboard/annual-returns/SimulationChart.tsx`

각 파일 200~400줄 가이드라인 준수.

### 3.4 데이터 페치
- 과거 트래킹: `useQuery(["analytics", "annual-returns"])`, staleTime 1시간 (월별 수익률과 동일).
- 시뮬레이션: `useMutation` 으로 POST. 결과는 클라이언트 state 보관.
- 파라미터 저장: `useMutation` PUT, onSuccess 시 react-query invalidate.

---

## 4. 색상 / UX

- 한국 컨벤션 준수: 수익 > 0 → 빨강, < 0 → 파랑.
- IRR 셀: 절댓값에 따라 채도 조절 (선택, MVP 후).
- 모바일: 표는 가로 스크롤. 차트는 ResponsiveContainer 100% 폭.

---

## 5. 테스트

### 5.1 백엔드 단위
- `xirr` 함수: 표준 케이스 (10% 일정 적립 → 약 0.10), 수렴 실패 케이스, 단일 cashflow 케이스.
- `annual-returns` API: 거래 없는 사용자 → []; 외화 거래 환산; 연중 첫 매수.
- `retirement-simulation`: bop * (1+r) + flow 공식 검증, 종료조건.

### 5.2 프론트엔드
- `AnnualReturnsTable` 렌더링 (양수/음수 색상).
- `SimulationForm` validation (음수 입력, end_age < retirement_age).

### 5.3 E2E (선택)
- 로그인 → 페이지 진입 → 시뮬레이션 실행 → 차트 렌더 확인.

---

## 6. 성능

- IRR 계산: 사용자 거래내역 보통 수십~수백 건 → brentq 1초 이내. 캐시 1시간.
- 시뮬레이션: 0~70 iterations, 클라이언트에서도 가능하나 입력 검증/저장 위해 서버 경유.

---

## 7. 리스크 / 미해결 사항

- IRR 가 수렴 안 하는 케이스 (극단 손실, 짧은 기간) — null 반환 + UI 에서 "—" 표시.
- 사용자가 birth_year 미입력 → 나이 컬럼 숨김. 시뮬레이션 폼은 현재 나이 직접 입력으로.
- 환율 변동이 외화 자산 수익률에 큰 영향 — KRW 기준 단일 통화로 계산해도 사용자 직관과 일치.

---

## 8. 작업량 추정

| 영역 | 예상 |
|------|------|
| Backend (Alembic + IRR utils + 3 APIs + tests) | 6h |
| Frontend (페이지 + 6 컴포넌트 + 차트 2개) | 6h |
| 통합 테스트 + 문서 | 2h |
| **합계** | **~14h** |

태스크 단위 break-down 은 `docs/plan/tasks.md` 의 `Feature: Annual Returns Menu` 섹션 참고.
