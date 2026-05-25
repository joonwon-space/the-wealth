# Feature: 자산 시뮬레이션 (Asset Simulation)

> **Replaces**: `feature-annual-returns.md` (deprecated).
> 이전 "연간 수익률 / 은퇴 시뮬레이션" 메뉴를 **포트폴리오와 완전히 분리된 순수 입력 기반 시뮬레이터** 로 교체.

배경: 사용자는 종목 단위 IRR 추적이 아니라 **"연도별로 얼마 적립 / 얼마 수익률로 운용해서 얼마 모이는지"** 를 자유롭게 가정할 수 있는 도구가 필요. 참고 시트
(`1u0Z_TS51nIK2gg86fGAtl5igdHG_UurmON7ZgyuJxWc`) 의 구조와 동일 공식 채택.

---

## 1. 시트 분석 결과 — 채택할 공식

5컬럼 × 69행 (32세~100세), 32~54세 적립 단계, 55~100세 인출 단계.

실수치 역산:
- **32세 (2024)**: bop=0, flow=₩3,960,000, rate=22.35% → eop=₩4,845,060
  - `(0 + 3,960,000) × 1.2235 = 4,845,060` ✓
- **33세 (2025)**: bop=4,845,060, flow=₩4,800,000, rate=15.25% → eop=₩11,115,932
  - `(4,845,060 + 4,800,000) × 1.1525 = 11,115,932` ✓
- **55세 (2047, 인출 시작)**: bop=276,453,756, flow=-₩15,000,000, rate=7% → eop=₩279,755,519
  - `(276,453,756 - 15,000,000) × 1.07 = 279,755,519` ✓

> **공식: `eop = (bop + flow) × (1 + rate)`** ("연초 적립/인출 후 1년 운용" 모델)
>
> 기존 구현은 `eop = bop × (1+r) + flow` 였으므로 **공식 자체가 달라 재구현 필수**.

연도별로 `flow` 와 `rate` 가 모두 달라질 수 있어 (32세 22.35%, 33세 15.25%, 34세부터 7%
고정) 전역 단일 파라미터로는 표현 불가 → **행 단위 인라인 편집 필수**.

---

## 2. 결정 사항 (사용자 컨펌 완료)

| 항목 | 결정 |
|------|------|
| 메뉴명 / 경로 | "자산 시뮬레이션" / `/dashboard/simulation` |
| 데이터 소스 | 사용자 입력 only (포트폴리오 무관) |
| 공식 | `eop = (bop + flow) × (1 + rate)` |
| 수정 UX | 표 셀 클릭 → 인라인 편집 (Excel 식) |
| 시나리오 수 | 1개 (`users.simulation_params` JSONB 재사용) |
| 이전 구현 | **완전 제거** (대체) |
| 수익률 | 명목만 (인플레/세금 미고려) |
| 기본값 채움 | 행 생성 시 `default_return_rate` 일괄, 이후 셀별 편집 |
| 적립/인출 전환 | 메타의 `retirement_age` 기준 자동 부호 결정 |

---

## 3. 데이터 모델

### 3.1 저장 스키마 (`users.simulation_params` JSONB)

```python
class SimulationMeta(BaseModel):
    current_age: int                  # 1..120
    start_year: int                   # 1900..2200
    end_age: int                      # current_age..120
    retirement_age: int               # current_age..end_age
    initial_balance_krw: float = 0
    accum_annual_krw: float = 0       # 적립 단계 기본 연 적립
    withdrawal_annual_krw: float = 0  # 인출 단계 기본 연 인출 (양수 입력)
    default_return_rate: float = 0.07 # 0.07 = 7%


class SimulationRow(BaseModel):
    age: int
    year: int
    flow_krw: float       # 적립(+) / 인출(-)
    return_rate: float    # 소수


class SimulationData(BaseModel):
    meta: SimulationMeta
    rows: list[SimulationRow]
```

기존 컬럼 그대로 사용 → **Alembic 마이그레이션 불필요**.
이전 형태(`SimulationInput` 단일 오브젝트)와는 구조가 달라 PUT 시 자동으로 덮어쓰여짐.

### 3.2 행 자동 생성 규칙

`[행 생성]` 버튼 클릭 시 `current_age..end_age` 행 일괄 생성:
- `age = current_age + offset`, `year = start_year + offset`
- `flow_krw = age < retirement_age ? +accum_annual_krw : -withdrawal_annual_krw`
- `return_rate = default_return_rate`

이미 행이 있으면 confirm 후 덮어쓰기.

---

## 4. API

### `GET /api/v1/simulation/params`
- **Auth**: Required
- **Response** (200): `SimulationData | null` — 저장 안 됐으면 null
- **Notes**: `users.simulation_params` 읽기. 본인만.

### `PUT /api/v1/simulation/params`
- **Auth**: Required
- **Body**: `SimulationData`
- **Response** (200): `SimulationData` (저장된 값 echo)
- **Notes**: Pydantic 검증 후 JSONB 덮어쓰기. 계산은 클라이언트에서 수행하므로 서버는 저장만.

---

## 5. 프론트엔드 구성

### 5.1 라우트 및 디렉토리
```
frontend/src/app/dashboard/simulation/
  page.tsx                 # 메타 폼 + 표 + 차트 컨테이너
  types.ts                 # SimulationMeta / SimulationRow / SimulationData / Derived
  SimulationMetaForm.tsx   # 메타 입력 + [행 생성] 버튼
  SimulationTable.tsx      # 인라인 편집 표 + 자동 계산
  SimulationSummary.tsx    # 요약 카드 6개
  SimulationChart.tsx      # Recharts AreaChart
```

### 5.2 표 컬럼

| 컬럼 | 편집 | 출처 |
|------|------|------|
| 나이 | ❌ | 자동 |
| 연도 | ❌ | 자동 |
| 적립/인출 | ✅ | 사용자 입력 (KRW, 음수 허용) |
| 수익률 (%) | ✅ | 사용자 입력 (소수 입력 받아 %로 표시) |
| 연초 잔고 | ❌ | 전년 연말 잔고 (첫 행은 `initial_balance_krw`) |
| 연말 잔고 | ❌ | `(bop + flow) × (1 + rate)` |
| 누적 적립 | ❌ | Σ flow (양수만) |
| 누적 수익 | ❌ | eop − bop_first − Σ flow |

인라인 편집: 셀 클릭 → `<input type="number">` 로 in-place 전환. blur/Enter 시 commit.
편집 시 derived 컬럼은 `useMemo` 로 즉시 재계산.

### 5.3 요약 카드 6개
- 종료 시점 잔고 (마지막 행 eop)
- 적립 단계 마지막 잔고 (age == retirement_age - 1 의 eop)
- 총 적립액 (Σ flow > 0)
- 총 인출액 (Σ |flow| where flow < 0)
- 총 운용 수익 (마지막 eop − initial_balance − Σ flow)
- 단순 평균 수익률 (rows 의 산술평균)

### 5.4 Area 차트
- X: age, Y: eop_krw
- 단일 시리즈, 그라데이션 fill
- `retirement_age` 에 ReferenceLine (점선 + "은퇴" 라벨)
- 한국 컨벤션: 양수 단조 증가 → 빨강 계열

---

## 6. 메뉴 / 진입점

- 사이드바 `Sidebar.tsx`: "분석" 다음에 **"자산 시뮬레이션"** (CalendarRange 아이콘) 추가.
- 모바일 BottomNav: 변경 없음 (4 슬롯 고정).
- `/dashboard/annual-returns` 라우트는 **404 처리** (디렉토리 삭제로 자연 404).

---

## 7. 삭제 범위 (이전 구현)

### Backend
- `app/api/analytics_annual.py`
- `app/services/annual_returns.py`
- `app/services/irr_utils.py` + `tests/test_irr_utils.py`
- `app/schemas/analytics.py` 의 `AnnualReturn`, `SimulationInput`, `SimulationPoint`
- `app/api/users.py` 의 `birth-year` / 이전 `simulation-params` 핸들러
- `app/schemas/user.py` 의 `BirthYearUpdate`
- `app/main.py` 의 `analytics_annual` import / `include_router`
- `services/analytics_utils.py` 의 `annual-returns` 캐시 키
- `users.birth_year` 컬럼은 **유지** (향후 다른 메뉴에서 재활용 가능, drop 불필요)
- `users.simulation_params` 컬럼은 **유지** (새 스키마로 재사용)

### Frontend
- `app/dashboard/annual-returns/` 디렉토리 전체 (8 파일)
- `app/dashboard/analytics/page.tsx` 의 진입 카드 Link + import
- `components/Sidebar.tsx` "연간 수익률" 항목 (새 항목으로 교체)

### Docs
- `docs/architecture/feature-annual-returns.md` → DEPRECATED 헤더 추가 후 보존 (히스토리)
- `docs/architecture/api-reference.md` 의 옛 엔드포인트 5개 (annual-returns, retirement-simulation, birth-year, simulation-params×2)
- `docs/plan/tasks.md` 의 AR-* 섹션은 completed 상태로 유지 (히스토리)

---

## 8. 테스트

### Backend
- `tests/test_simulation_api.py` (신규):
  - GET 빈 상태 → null
  - PUT 정상 데이터 → 200 + 반환
  - PUT 잘못된 type → 422
  - 본인 외 사용자 접근 차단 확인

### Frontend
- Type check + ESLint + `next build`
- 인라인 편집 단위 테스트는 우선 생략 (수동 검증).

### E2E
- 사이드바 메뉴 진입 → 메타 입력 → [행 생성] → 셀 수정 → 차트/요약 갱신 확인
- [저장] → 새로고침 → prefill 복원 확인

---

## 9. 작업 분해 (`docs/plan/tasks.md` 참조)

| Task | 영역 | 예상 |
|------|------|------|
| TASK-SIM-1 | 이전 annual-returns 자산 완전 제거 | 1h |
| TASK-SIM-2 | simulation 스키마 + 백엔드 API | 1.5h |
| TASK-SIM-3 | 프론트 페이지 + 메타 입력 폼 | 1.5h |
| TASK-SIM-4 | 인라인 편집 표 + 자동 계산 | 2.5h |
| TASK-SIM-5 | 요약 카드 + Area 차트 | 1h |
| TASK-SIM-6 | 사이드바 메뉴 + 저장/불러오기 | 1h |
| TASK-SIM-7 | 문서 갱신 + devlog | 0.5h |
| **합계** | | **~9h** |

---

## 10. 미해결 / 향후 확장

- **CSV 내보내기/가져오기**: 시트에서 작업한 사용자가 한 번에 import 하고 싶을 때. v2 후보.
- **여러 시나리오**: 보수/중립/공격 비교. v2 에 `simulation_scenarios` 테이블 추가 검토.
- **인플레이션 보정**: 실질 수익률 토글. v2.
- **나이→연도 자동 정렬**: end_age 변경 시 행 재생성 vs 부분 추가/축소 — 현재는 단순 confirm 후 일괄 재생성.
- **stress test**: -10% 같은 극단 시나리오 시 잔고가 음수가 될 때 0 으로 클램프할지 그대로 둘지 — **현재는 그대로** (잔고 음수 = 자산 소진 시점 시각화에 유용).
