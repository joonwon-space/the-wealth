# The Wealth — Design System

**The Wealth (더 웰스)** 는 한국투자증권(KIS) OpenAPI 기반의 개인 자산관리 대시보드 입니다. 실시간 포트폴리오 현황, 수익률 분석, 섹터 배분, 관심종목, 캔들스틱 차트, 가격 알림 등을 한 화면에서 다룹니다. 이 디자인 시스템은 **웹 대시보드**(Next.js 16 + React 19 + Tailwind v4 + shadcn/ui)와 **모바일 앱** 두 제품을 모두 커버합니다.

## 소스

이 디자인 시스템은 아래 산출물에서 파생되었습니다. 독자가 접근 권한이 없을 수 있으니 사본을 같이 보관합니다:

- **Frontend 코드베이스** — `frontend/src/` (Next.js App Router, `components/ui/` 가 shadcn/ui, `app/globals.css` 에 토큰)
- **design-system.md** — 토큰 맵, shadcn 설정, 한국 증시 색 규칙, cn() helper
- **docs/architecture/overview.md, analysis.md, frontend-guide.md** — 페이지 구조, 컴포넌트 트리, 훅

지금 이 프로젝트의 파일 시스템에는 코드베이스가 복제되어 있지 않고 위 문서들을 기반으로 재구성되었습니다. Pixel-perfect 추출이 필요하면 Import 메뉴에서 `the-wealth` 리포지토리를 붙여주세요.

---

## Index — 파일 안내

| 파일 | 용도 |
|---|---|
| `SKILL.md` | Claude Code / Agent Skills 호환 엔트리포인트 |
| `README.md` | (이 파일) 브랜드 컨텍스트, 콘텐츠·비주얼 파운데이션, 인덱스 |
| `design-system.md` | shadcn/ui 설정, Tailwind v4 `@theme inline` 토큰 맵, cn() helper, 다크 모드 |
| `korean-market-colors.md` | 한국 증시 상승=빨강/하락=파랑 컨벤션 가이드 |
| `component-checklist.md` | 새 컴포넌트 작성 시 체크리스트 |
| `colors_and_type.css` | 드롭인 CSS — 색상/타이포 토큰과 `h1`, `p`, `code` 시맨틱 변수 |
| `assets/` | 로고, 일러스트, 정적 이미지 (없으면 비어 있음) |
| `fonts/` | 웹폰트 — 현재는 시스템 스택 사용, 별도 파일 없음 |
| `preview/` | Design System 탭에 렌더되는 카드 HTML |
| `ui_kits/web/` | 웹 대시보드 UI kit (index.html + JSX 컴포넌트) |
| `ui_kits/mobile/` | 모바일 앱 UI kit (index.html + JSX 컴포넌트) |

UI kit과 slides 는 아직 이 패키지 안에서 부분적으로만 생성됩니다. 필요한 서피스를 요청하시면 채워드립니다.

---

## Content Fundamentals — 콘텐츠 파운데이션

**언어**. UI 레이블은 **한국어 기본**. 예: "포트폴리오", "관심종목", "거래내역", "수익률", "보유 수량", "평가손익", "실현손익", "매수", "매도". 영어는 약어/고유명사에 한해(KIS, CSV, JWT, Redis 등) 허용.

**호칭/시점**. 사용자를 **직접 지칭하지 않습니다**(당신/님/you 모두 안 씀). 대부분의 UI 카피는 **명사구 + 숫자** 중심("보유 종목 24개", "총 평가금액 ₩42,180,500") 혹은 **동사 원형 액션 버튼**("추가", "저장", "편집", "삭제", "내보내기").

**케이싱**. 한국어는 케이싱 개념이 없으므로 영어 토큰만 주의:
- 버튼/액션 영어 단어 — Title Case ("Export CSV", "Sign In")
- 기술 용어 — 소문자 그대로 ("JWT", "KIS API", "openapi")
- 섹션 타이틀 — 한국어 짧은 명사구 ("보유 종목", "최근 거래", "섹터 배분")

**숫자 표기**. 금액은 **원화 기호(₩) 또는 "원" 접미사** + **천 단위 콤마**. 소수점은 대개 2자리 (수익률/환율). 예: `₩42,180,500`, `+3.24%`, `1,250주`.

**부호**. 양수에는 `+` 를 **명시**합니다. "+3.24%", "+₩1,204,000". 음수는 `-` 만 (마이너스 기호).

**에러/빈 상태 톤**. 간결·중립. "데이터가 없습니다." / "불러오는 중...". 과장·사과 톤(죄송합니다~, 오 이런!) 지양.

**이모지**. **사용 안 함** (차트/데이터 중심 금융 UI). 상태 표시는 색상 + 아이콘(Lucide) 조합으로.

**Vibe**. **차분하고 정밀한 계기판**. 증권사 HTS 의 과포화된 색·숫자 폭격보다 한 단계 덜어낸, 데스크톱 앱에 가까운 데이터 밀도. 흰 배경에 푸른 포인트(dodger blue), 상승/하락은 빨강/파랑 두 색으로만. 쿨한 bluish-gray neutral, 장식 요소 최소화.

### 예시 카피

> 섹션 타이틀: **보유 종목**
> 빈 상태: 보유 중인 종목이 없습니다. 우측 상단 **추가** 버튼으로 시작하세요.
> 알림 토스트: 가격 알림이 설정되었습니다.
> 버튼 레이블: **추가 / 저장 / 편집 / 삭제 / 내보내기 / 동기화**
> 등락률 포맷: **+3.24%** / **-1.08%** / **0.00%**

---

## Visual Foundations — 비주얼 파운데이션

### 색 (Color)

- **Base palette**: shadcn `neutral` (회색 기반). oklch로 정의된 뉴트럴 스케일 — `--background`, `--foreground`, `--muted`, `--muted-foreground`, `--border`, `--card`, `--card-foreground`, `--popover`, `--accent`, `--secondary`.
- **Primary**: **Dodger blue #1e90ff**. 링크, CTA, 포커스 링, 선택된 탭, 포트폴리오 라인차트 기본색.
- **Korean market colors**: `--rise #E31F26` (상승, 빨강), `--fall #1A56DB` (하락, 파랑). 다크 모드에서 WCAG AA 를 맞추려 `#FF4D4F` / `#4B8EF5` 로 전환.
- **Destructive**: 빨강 계열 — 단, 한국 증시 문맥에서 **"빨강 = 상승"** 이므로 destructive 버튼은 별도 `--destructive` 토큰 사용하고 손실 수치와 나란히 쓰지 않도록 배치 주의.
- **Chart palette (8색)**: `#1e90ff, #00ff00(라이트)/green(다크), amber #F59E0B, rose #F43F5E, violet #8B5CF6, cyan #06B6D4, orange #F97316, green #22C55E`.
- **Accents**: `#00ff00` 네온 그린 — 라이트 모드 차트 보조색으로만 사용. 일반 UI chrome 에는 쓰지 않음.

라이트/다크 모두 oklch 기반으로 자동 조정됩니다. 다크 모드에서는 채도를 살짝 높이고 `--rise`/`--fall` 을 밝게 전환해 가독성을 맞춥니다.

### 타이포 (Type)

- **Font family**: 시스템 스택 기본. 영문은 `ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, ...`, 한글은 `Pretendard → Apple SD Gothic Neo → Noto Sans KR → sans-serif` 순. `Pretendard Variable` CDN 이 권장 1순위 (없으면 fallback 로 자연스럽게).
- **Mono**: `ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace` — 수치(가격, 수익률) 표기에 자주 사용.
- **Tabular nums**: 수치 표기에 `font-variant-numeric: tabular-nums` 필수. 컬럼 정렬이 틀어지지 않도록.
- **Type scale** (see `colors_and_type.css`):
  - `--text-display`: 36–44px, weight 700, -0.02em tracking — 히어로/대시보드 top metric
  - `--text-h1`: 28px / 700
  - `--text-h2`: 22px / 600
  - `--text-h3`: 18px / 600
  - `--text-body`: 14px / 400 — 기본
  - `--text-small`: 13px / 400 — 보조 설명, 테이블 sub text
  - `--text-micro`: 12px / 500, uppercase letter-spacing 0.04em — 레이블/배지
  - `--text-number`: 14–28px / 600, tabular, mono-ish — 가격·수익률

### 스페이싱 (Spacing)

Tailwind 기본 4px 그리드. 컴포넌트 내부 padding 은 `p-3` (12px) / `p-4` (16px), 카드 간 gap 은 `gap-4` (16px) / `gap-6` (24px). 섹션 gutter 는 `gap-6` / `gap-8`.

### 배경 / 레이아웃

- **배경은 대부분 단색**. `bg-background`(라이트: 거의 순백, 다크: 깊은 뉴트럴). 그라데이션·패턴·full-bleed 이미지 **사용 안 함**.
- 대시보드는 **좌측 사이드바 + 상단 헤더 + 메인 그리드** 구조. 사이드바 너비 240px 고정, 상단 56–64px, 메인은 12-column grid / `max-w-[1440px] mx-auto`.
- 카드 단위 정렬. full-bleed 이미지 × 금융 제품 톤 불일치.

### 카드 / 보더 / 그림자

- **Card**: `bg-card text-card-foreground border border-border rounded-lg` (radius 10px). 그림자는 **거의 안 씀** — 정보 위계는 border와 배경 대비로.
- 필요한 경우에만 `shadow-sm` (`0 1px 2px rgba(0,0,0,0.04)`). popover/dropdown 에는 `shadow-md` 1단계. 다크 모드에서는 그림자 대신 border 채도 올려 구분.
- **Inner shadow 사용 안 함**.

### 코너 라운딩

- **기본**: `rounded-lg` = 10px (카드, 모달, 큰 버튼)
- **입력/작은 버튼**: `rounded-md` = 8px
- **배지/태그**: `rounded-md` = 6px
- **동그란 아바타/차트 dot**: `rounded-full`
- 모바일에서는 iOS 느낌을 살려 카드를 `rounded-2xl` (16px) 한 단계 키움.

### 보더

- 기본 두께 **1px**. `--border` 는 뉴트럴 라이트 그레이(oklch 기반).
- 테이블 행 구분은 bottom border만. 풀 그리드 테이블(수평+수직 보더) 지양.

### 투명도 / 블러

- **Backdrop blur 거의 안 씀**. modal overlay 만 `bg-black/40` 반투명, blur 없음.
- hover 가벼운 투명도로 처리하는 대신 배경 컬러 단계로 전환 (`hover:bg-accent`, `hover:bg-muted`).

### 아이콘

- **Lucide (lucide-react)** 이 공식. stroke 1.75, 16/20/24px 세 사이즈만 사용. `size-4 / size-5 / size-6`.
- 자체 SVG 커스텀은 로고/브랜드 마크 한정. 데이터 시각화 기호는 Recharts / lightweight-charts 기본 심볼 사용.
- 상세는 `design-system.md` 의 Iconography 섹션 참고.

### 애니메이션

- **짧고 기능적**. easing은 `ease-out`, duration 150–200ms. 대부분 `transition-colors`, `transition-[opacity,transform]` 수준.
- Hover: 200ms 색/배경 전환. Press: `active:scale-[0.98]` 약한 축소. Bounce·overshoot **안 씀**.
- Skeleton 로딩: shadcn `Skeleton` 컴포넌트의 부드러운 pulse만. 스피너는 데이터 새로고침 때 24px Lucide `RefreshCw` 회전.
- 데이터 업데이트: 숫자가 바뀔 때 200ms `bg-rise/10` 또는 `bg-fall/10` 플래시 (옵션).

### 호버 / 프레스 상태

- **Hover**
  - 일반 버튼: primary → `bg-primary/90`, ghost → `bg-accent text-accent-foreground`
  - 테이블 행: `hover:bg-muted/50`
  - 링크 텍스트: 색 동일, `underline` on hover
- **Focus**: `ring-2 ring-ring ring-offset-2` (ring은 primary 계열).
- **Active/Press**: `active:scale-[0.98]` (큰 버튼), 작은 버튼은 그냥 색만 더 진하게.
- **Disabled**: `opacity-50 pointer-events-none`.

### 이미지 / 그래픽 톤

- 금융 대시보드 특성상 사진/일러스트 거의 없음. 있다면 **차분한 뉴트럴 톤, 그레인·텍스처 없음**. 색 온도는 cool. 따뜻한 세피아/빈티지 톤 지양.

### 레이아웃 규칙

- 대시보드 메인 영역은 **고정 폭 없음**, 반응형 12-col grid. `max-w-[1440px]` 중앙 정렬.
- 모바일: 세이프 에리어 준수, 하단 탭바 높이 56 + safe-area-inset-bottom.
- 상단 헤더는 `sticky top-0 z-40 bg-background/95 backdrop-blur-sm` — 여기만 예외적으로 약한 blur 허용.

자세한 토큰 값은 `design-system.md` 와 `colors_and_type.css` 참조.

---

## Iconography

- **공식 아이콘 라이브러리**: **Lucide** (`lucide-react`). shadcn `iconLibrary: "lucide"` 설정과 일치.
- **스트로크**: 1.75 (Lucide 기본), 사이즈 16 / 20 / 24 px 세 단계 (`size-4 size-5 size-6`).
- **컬러**: `text-muted-foreground` 기본, 활성 상태만 `text-foreground` 또는 `text-primary`.
- **사용되는 아이콘들** (추정 / 관찰):
  - Navigation: `LayoutDashboard, Wallet, TrendingUp, PieChart, Bell, Search, Settings`
  - Actions: `Plus, Pencil, Trash2, Download, Upload, RefreshCw, MoreHorizontal`
  - Status: `ArrowUp, ArrowDown, Minus, AlertTriangle, CheckCircle2`
  - Market: `CandlestickChart, LineChart, BarChart3, Star` (관심종목), `Eye, EyeOff`
  - Theme: `Sun, Moon`
  - Auth: `LogIn, LogOut, User, KeyRound`
- **PNG 아이콘 / 이모지 / 유니코드 심볼 사용 안 함.** 수치 표기에서 상승/하락 방향은 Lucide `ArrowUp/ArrowDown` + `--rise` / `--fall` 색 조합.
- **Logo / 브랜드 마크**: 이 패키지에는 실제 로고 파일이 포함되어 있지 않습니다 (사용자가 지급 시 `assets/logo.svg` 자리에 배치). 로고가 없을 때는 워드마크("The Wealth", display 타입, weight 700, tracking -0.02em, primary 컬러) 로 대체합니다.

---

## Caveats (현재 상태)

- **실제 코드베이스 접근 불가**. README/design-system.md 인라인 내용만으로 재구성했습니다. 정확한 spacing/layout/copy를 원하시면 리포지토리를 Import 해주세요.
- **웹폰트 파일 미포함**. Pretendard 를 권장하지만 번들하지 않았습니다 — CDN 링크 또는 `fonts/` 에 직접 추가해 주세요.
- **로고·브랜드 이미지 미포함**. 지급받는 대로 `assets/` 에 넣겠습니다.
- **UI kit 은 재구성본**. 실제 화면과 구성은 일치하나 픽셀 단위 정합성은 코드베이스 접근 후 보정 필요.

자세한 응답 요청은 `SKILL.md` 의 guidance 를 따라 사용자에게 질문하고 이터레이트합니다.
