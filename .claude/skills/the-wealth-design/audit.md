# Phase 1 — Data Audit · 데이터 인벤토리 · 현 UI 매핑 · 갭 분석

> **목적**: 개편 방향을 결정하기 전에 "우리가 실제로 가진 데이터"와 "지금 보여주고 있는 것"의 차이를 문서화한다. 이 문서는 Phase 2(개편 방향 5가지 비교)의 기반 자료다.
>
> **범위**: `the-wealth/backend/app/models/`, `app/api/`, `app/schemas/` + `frontend/src/app/dashboard/` 기준
>
> **전제 (사용자 확인)**: 전면 개편 · 모바일≒웹 1급 · 북극성=빠른 현황 파악(토스 스타일) · 페르소나=장기70/단타30 혼합 · 톤=전문·간결(한투 MTS 스타일) · 필요 시 새 테이블/외부 API 연동 OK

---

## 1. 데이터 인벤토리

### 1.1 엔티티 맵

```
User ──┬── Portfolio ──┬── Holding      (보유 종목)
       │               ├── Transaction  (체결 내역, BUY/SELL, memo, tags[])
       │               └── Order        (주문, pending/filled/cancelled)
       ├── KisAccount  (한투 API 연동, 복수 계좌: 일반/ISA/연금저축/IRP/해외)
       ├── Alert       (목표가 알림)
       ├── Notification(트리거된 알림 로그)
       └── Watchlist   (관심 종목)

전역 스냅샷 테이블:
  PriceSnapshot    ticker × date  OHLCV (일봉)
  IndexSnapshot    KOSPI200 · S&P500 벤치마크
  FxRateSnapshot   USDKRW 일별 종가
```

### 1.2 필드 상세

| 테이블 | 주요 필드 | 비고 |
|---|---|---|
| **Portfolio** | `name`, `currency`, `kis_account_id`, `display_order`, `target_value` | `target_value` = **목표 자산** (BigInt, 사용자 목표 설정용). 현재 UI에서 활용 低 |
| **Holding** | `ticker`, `name`, `quantity`, `avg_price`, `market` (NAS/NYS 등) | 현재가·손익은 동적 계산 (KIS API) |
| **Transaction** | `type` (BUY/SELL), `quantity`, `price`, `traded_at`, `memo`, `tags[]`, `order_source` (manual/kis) | **memo·tags 필드가 있으나 현 UI에 노출 부족** |
| **Order** | `order_type`, `order_class` (limit/market), `status`, `filled_quantity`, `filled_price` | 실시간 주문 상태 추적 가능 |
| **Alert** | `condition` (above/below), `threshold`, `is_active`, `last_triggered_at` | 목표가 알림만 지원 (수익률/낙폭 알림 없음) |
| **Watchlist** | `ticker`, `market` | 관심종목. 메모·태그·정렬 없음 |
| **KisAccount** | `label`, `account_no`, `account_type` (일반/ISA/연금저축/IRP/해외), `is_paper_trading` | **계좌 타입별 구분 가능하나 UI 미반영** |

### 1.3 계산 가능한 지표 (데이터 기반)

현 DB 만으로 계산 가능한 것들 — 일부는 API가 있고 일부는 **있는데 안 보여주고 있음**.

| 지표 | 데이터 소스 | API 존재 | UI 노출 |
|---|---|---|---|
| 총 자산 (평가금액) | Holding × KIS 실시간 | ✅ `/dashboard/summary` | ✅ |
| 투자 원금 | Holding.quantity × avg_price | ✅ | ✅ |
| 총 손익 / 수익률 | 위 둘의 차 | ✅ | ✅ |
| **일일 변동** (금액·%) | PriceSnapshot + KIS 실시간 | ✅ `day_change_amount/pct` | ✅ (숫자만) |
| 섹터별 비중 | Holding + `data/sector_map.py` | ✅ `/analytics/sector-allocation` | ⚠️ 분석 탭 안쪽 |
| 월별 수익률 | Transaction + PriceSnapshot | ✅ `/analytics/monthly-returns` | ⚠️ 분석 탭 |
| 포트폴리오 히스토리 | Transaction + PriceSnapshot | ✅ `/analytics/portfolio-history` | ⚠️ 분석 탭 |
| 벤치마크 비교 (KOSPI200/S&P500) | IndexSnapshot | ✅ `/analytics/benchmark` | ❌ 미사용 |
| **환차손익 분리** | Transaction + FxRateSnapshot | ✅ `/analytics/fx-gain-loss` | ⚠️ 분석 탭 |
| SMA 이동평균 | PriceSnapshot | ✅ `/analytics/sma` | ⚠️ 분석 탭 |
| 종목별 보유 비중 | Holding | ✅ allocation | ✅ |
| 예수금 | KIS balance | ✅ `total_cash` | ✅ |
| **목표 진척도** | Portfolio.target_value ÷ 현재 자산 | ❌ 계산 로직 없음 | ❌ |
| 52주 고가·저가 | KIS API | ✅ `w52_high/low` | ⚠️ 숨겨짐 |
| 배당 | **데이터 없음** | ❌ | ❌ |
| 체결 대비 주문 성공률 | Order | ❌ | ❌ |

### 1.4 외부 API 연동

- **KIS OpenAPI**: 국내/해외 실시간 가격, 잔고, 주문, 환율, 벤치마크 지수
- **SSE 스트림**: 보유 종목 실시간 가격 (`usePriceStream`)
- **없는 것**: 배당 정보, 종목 뉴스, 공시, 재무제표 요약

---

## 2. 현재 화면 맵

### 2.1 페이지 구조

```
/login, /register
/dashboard                  대시보드 (홈)
/dashboard/portfolios       포트폴리오 목록
/dashboard/portfolios/[id]  포트폴리오 상세
/dashboard/analytics        분석 (metrics/history/monthly/sector-fx/performance/stock-chart)
/dashboard/compare          (용도 불명확)
/dashboard/journal          투자 일지
/dashboard/stocks           종목 검색/상세?
/dashboard/settings         설정
```

### 2.2 대시보드 홈 현황 (`/dashboard`)

현재 한 화면에 표시되는 것들:

1. 헤더 — 제목 + SSE 상태 + 새로고침 버튼
2. KIS 오류 배너 (조건부)
3. **총 자산 Large 카드** — 금액 + 일일 변동 + USD/KRW + 7일 스파크라인
4. **3칸 Metric 그리드** — 투자원금 · 예수금 · 총 손익
5. **PortfolioList** — 내부적으로 Holdings Table + Watchlist + Allocation Donut 포함
6. KIS 연동 포트폴리오라면: 주문 패널?

**측정한 문제점** (사용자 피드백 + 데이터 감사 결합):

| 증상 | 원인 추정 |
|---|---|
| 정보 과밀 | 한 스크롤 안에 5개 섹션, 모든 섹션이 1급 강조 |
| 좌우 스크롤 발생 | Holdings Table이 가로로 길고 모바일에서 오버플로 |
| 탭 이동 잦음 | 섹터 비중·월별 수익률·환차손익이 **전부 /analytics 안**에 숨어있어 홈 ↔ 분석 왕복 |
| 대형 차트 부재 | 스파크라인만 있고 메인 차트가 없어 "오늘 얼마 변했나"를 **숫자로만** 읽어야 함 (Robinhood/토스 모두 차트 우선) |
| "오늘의 인사이트" 없음 | 자산 3% 급락, 최대 mover 같은 요약 카드 전무 |

### 2.3 모바일 레이아웃 현황

- Sidebar → hamburger drawer 로 전환
- 동일한 데스크탑 위젯을 1열로 스택 → **모바일에 맞게 재구성되지 않음**
- BottomNav 컴포넌트는 존재하나 실제 App Shell 전환이 불완전해 보임 (layout 구조 확인 필요)

---

## 3. 갭 분석 — 있는데 못 쓰는 데이터

### 3.1 🔴 완전 활용 실패 (데이터·API 존재 · UI 부재)

1. **목표 자산 (Portfolio.target_value)** — 스키마에 있음, **"목표 진척도"** 시각화 0
2. **벤치마크 비교 (IndexSnapshot)** — KOSPI200/S&P500 스냅샷이 매일 들어오지만 "내 포트폴리오 vs 코스피" 비교 UI 없음
3. **Transaction.memo + tags[]** — 메모·태그 필드는 있으나 투자 일지에서만 쓰이고, 각 체결에 대한 회고 루프 없음
4. **Order status 흐름** — pending/filled/partial/cancelled 전체 상태가 있으나 "미체결 주문" 위젯이 홈에 없음

### 3.2 🟡 분석 탭에 묻혀있음 (홈에 올려야 할 것)

1. **섹터 비중** — 리밸런싱 인사이트의 핵심
2. **월별 수익률 히트맵** — "이번 달 -2.3%" 같은 한 줄 요약으로 홈에 내놓을 수 있음
3. **환차손익 분리** — 해외주식 보유자에게 1급 지표
4. **52주 고가·저가** — 보유 종목 건강 신호

### 3.3 🟠 데이터 부족 (백엔드 추가 필요)

개편 과정에서 **새로 확보해야 할 데이터**:

| 데이터 | 용도 | 구현 난이도 |
|---|---|---|
| **배당 데이터** (date, amount, ticker) | 배당 캘린더, 연 배당 수익률 | 중 (KIS 배당 API 있음) |
| **종목 뉴스 요약** | 홈 "오늘의 이슈" 카드 | 중~상 (외부 API: NAVER/네이버증권/Stockanalysis) |
| **리밸런싱 목표 비중** | "현재 IT 45% / 목표 30% → 매도 필요" | 저 (Portfolio에 target_allocation JSONB 추가) |
| **루틴 체크 로그** | 월 리밸런싱 체크 기록 | 저 (routine_logs 테이블) |
| **공시 일정** | 분기 실적 발표일 알림 | 중 |

---

## 4. 개편 방향에 영향을 줄 핵심 결정사항

Phase 2에서 5개 방향을 비교할 때 **축이 될 변수** 정리:

| 축 | 선택지 |
|---|---|
| **A. 홈 우선 정보** | A1 일일 변동 스포트라이트 · A2 목표 진척도 · A3 액션 Todo · A4 차트 중심 · A5 섹터/리밸런싱 인사이트 |
| **B. 정보 구조** | B1 단일 홈(모든 것) · B2 탭 분리(홈/보유/분석/주문) · B3 카드 피드(상황별 동적) · B4 Focus view(단일 포커스 + 주변 맥락) |
| **C. 차트 비중** | C1 없음 · C2 작은 스파크라인 · C3 주력 대형 차트 · C4 인터랙티브 드릴다운 |
| **D. 주문 노출** | D1 숨김 · D2 별도 탭 · D3 홈 하단 퀵액션 · D4 SwipeAction 바로가기 |
| **E. 리밸런싱·루틴** | E1 없음 · E2 월간 카드 · E3 상시 대시보드 · E4 목표 대비 실시간 경고 |
| **F. 일지·회고** | F1 숨김 · F2 체결 내역 병합 · F3 독립 섹션 · F4 체결 후 즉시 프롬프트 |

---

## 5. 제약 · 보존 사항

사용자 명시:
- ✅ KIS API 연동 로직 보존
- ✅ SSE 실시간 가격 스트림 보존
- ✅ 매수/매도 시스템 보존
- ✅ 한국 증시 색 규칙 (상승=빨강, 하락=파랑)
- ✅ 한국어 UI

---

## 6. 다음 단계

Phase 2 에서 위 **A~F 6개 축을 조합한 5가지 개편 방향**을 `directions.html` 에 나란히 제시:

- **D1 · Glance** — 빠른 현황 파악 극대화 (북극성 그대로)
- **D2 · Studio** — 차트·종목 상세 몰입
- **D3 · Mission Control** — 목표 진척도·리밸런싱 경고·루틴 체크 우선
- **D4 · Stream** — 카드 피드 (상황별 카드 동적 노출)
- **D5 · Dual Brain** — 장기(수익률·배당·목표) / 단타(실시간·미체결·mover) 모드 전환

각 방향은 IA 다이어그램 + 모바일 홈 썸네일 + 장단점 + 구현 비용 추정으로 구성한다.
