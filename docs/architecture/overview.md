# 프로젝트 개요

## 1. 프로젝트 목적

The Wealth는 한국투자증권(KIS) OpenAPI를 활용한 **개인 자산관리 대시보드**입니다. 증권사 계좌와 연동하여 보유 종목의 현재가, 수익률, 자산 배분을 실시간으로 파악하고, 포트폴리오 히스토리 및 월별 수익률 분석을 통해 투자 의사결정을 지원합니다.

### 핵심 가치

- **실시간 현황 파악**: KIS API를 통한 실시간 현재가 조회 및 SSE 스트리밍
- **자동 동기화**: 증권사 계좌와 1시간 주기 자동 동기화로 수동 입력 최소화
- **투자 분석**: 월별 수익률 히트맵, 섹터별 자산 배분, 포트폴리오 히스토리 차트
- **보안 우선**: KIS API 자격증명 AES-256-GCM 암호화 저장, JWT 인증

### 대상 사용자

- 한국투자증권 계좌를 보유한 개인 투자자
- 포트폴리오 성과를 체계적으로 추적하고자 하는 사용자
- 국내/해외 주식을 함께 관리하고자 하는 사용자

---

## 2. 기능 명세

### 2.1 인증 및 사용자 관리

| 기능 | 설명 |
|------|------|
| 회원가입 | 이메일 + 비밀번호, bcrypt 해싱 |
| 로그인 | JWT access token (30분) + refresh token (7일) 발급 |
| 토큰 갱신 | Refresh token rotation — 1회성 JTI 소비 후 새 토큰 쌍 발급 |
| 비밀번호 변경 | 기존 비밀번호 확인 후 변경, 모든 refresh token 무효화 |
| KIS 계좌 등록 | App Key/Secret을 AES-256-GCM으로 암호화하여 저장 |
| KIS 계좌 테스트 | 등록된 자격증명으로 토큰 발급 테스트 |

### 2.2 포트폴리오 관리

| 기능 | 설명 |
|------|------|
| 포트폴리오 CRUD | 생성, 조회, 수정, 삭제 |
| 보유종목 관리 | 종목 추가/수정/삭제, 수량/평균 매입가 관리 |
| 거래내역 기록 | BUY/SELL 거래 기록, 자동 보유종목 수량 반영 |
| CSV 내보내기 | 포트폴리오 보유종목 및 거래내역 CSV 다운로드 |
| KIS 계좌 연결 | 포트폴리오에 KIS 계좌를 1:1 매핑 |

### 2.3 대시보드

| 기능 | 설명 |
|------|------|
| 포트폴리오 요약 | 총 자산, 총 수익/손실, 수익률 |
| 보유종목 테이블 | TanStack Table v8 기반 멀티 컬럼 정렬, 현재가/수익률 표시 |
| 자산 배분 차트 | Recharts 도넛 차트 + 중앙 오버레이 텍스트 |
| 실시간 가격 | SSE(Server-Sent Events) 기반 30초 주기 가격 업데이트 (사용자별 최대 3연결, 15초 하트비트, 2시간 타임아웃) |
| 30초 폴링 | 대시보드 데이터 자동 갱신 |

### 2.4 분석 및 차트

| 기능 | 설명 |
|------|------|
| 수익률 지표 | 총 수익률, 일간 변동률 등 핵심 지표 |
| 월별 수익률 히트맵 | 월별 수익률을 히트맵으로 시각화 |
| 포트폴리오 히스토리 | 기간별 포트폴리오 가치 변동 추이 |
| 섹터별 배분 | 보유종목의 섹터별 비중 분석 |
| 캔들스틱 차트 | lightweight-charts 기반 일봉 차트 |
| 일별 OHLCV 차트 | KIS API 일별 시가/고가/저가/종가/거래량 |

### 2.5 종목 검색 및 관심종목

| 기능 | 설명 |
|------|------|
| Cmd+K 검색 | 키보드 단축키로 종목 검색 다이얼로그 호출 |
| 종목 상세 | 개별 종목의 현재가, 상세 정보 조회 |
| 관심종목 | 관심 종목 추가/삭제, KRX/NYSE/NASDAQ 마켓 구분 |

### 2.6 알림

| 기능 | 설명 |
|------|------|
| 가격 알림 설정 | 특정 종목의 목표가 상한/하한 알림 등록 |
| 알림 관리 | 활성/비활성 토글, 삭제 |

### 2.7 자동 동기화

| 기능 | 설명 |
|------|------|
| KIS 계좌 동기화 | APScheduler 기반 1시간 주기 자동 동기화 |
| 수동 동기화 | 즉시 동기화 트리거 |
| 동기화 로그 | 동기화 이력 조회 (inserted/updated/deleted 건수) |
| 일일 종가 스냅샷 | 평일 KST 16:10 보유종목 OHLCV 자동 저장 |

---

## 3. 페이지 구조

```
/                           → 루트 (로그인 리다이렉트 또는 랜딩)
/login                      → 로그인 페이지
/register                   → 회원가입 페이지
/dashboard                  → 메인 대시보드
  ├── /                     → 포트폴리오 요약 + 보유종목 테이블 + 자산 배분 차트
  ├── /analytics            → 수익률 분석 (월별 히트맵, 포트폴리오 히스토리)
  ├── /portfolios           → 포트폴리오 목록
  ├── /portfolios/[id]      → 포트폴리오 상세 (거래내역, 보유종목)
  ├── /stocks/[ticker]      → 종목 상세 (캔들스틱 차트, 종목 정보)
  └── /settings             → KIS 계좌 관리, 사용자 설정
```

### 네비게이션

- **사이드바 (Sidebar)**: 데스크톱 환경에서 주요 페이지 이동
- **하단 네비게이션 (BottomNav)**: 모바일 환경에서 탭 기반 이동
- **Cmd+K 다이얼로그**: 어디서든 종목 검색 가능

---

## 4. UI/UX 설계 원칙

### 4.1 한국 증시 컬러 컨벤션

한국 증시의 표준 컬러 규약을 준수합니다:

| 상태 | 색상 | 적용 컴포넌트 |
|------|------|--------------|
| 상승 (양수 수익률) | **빨간색 (Red)** | `PnLBadge`, `DayChangeBadge` |
| 하락 (음수 수익률) | **파란색 (Blue)** | `PnLBadge`, `DayChangeBadge` |
| 보합 (0%) | 중립 (Gray) | `PnLBadge`, `DayChangeBadge` |

이는 미국/유럽(상승=초록, 하락=빨강)과 반대되는 한국 시장 고유의 컨벤션입니다.

### 4.2 데이터 밀도 계층

정보 우선순위에 따라 시각적 계층을 구성합니다:

1. **최상위**: 총 자산, 총 수익률 — 대시보드 상단 대형 텍스트
2. **중간**: 개별 종목 현재가/수익률 — 보유종목 테이블 내 강조
3. **보조**: 섹터 배분, 월별 히트맵 — 차트 및 시각화 영역
4. **상세**: 거래내역, 동기화 로그 — 서브 페이지 또는 드릴다운

### 4.3 모바일 퍼스트 설계

- 반응형 레이아웃: Tailwind v4 반응형 유틸리티 활용
- 모바일 하단 네비게이션 (`BottomNav` 컴포넌트)
- 터치 친화적 인터랙션 (충분한 터치 영역, 스와이프 지원)
- 데스크톱 사이드바 + 모바일 하단 탭 이중 네비게이션 구조

### 4.4 다크 모드

- `next-themes` 기반 시스템/수동 테마 전환
- shadcn/ui `base-nova` 스타일 + `neutral` 기본 색상
- 차트 컴포넌트 테마 연동

---

## 5. API 엔드포인트 전체 목록

총 49개 엔드포인트 (모두 `/api/v1` prefix, 내부 API 별도):

### 인증 (5)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/register` | 회원가입 |
| POST | `/auth/login` | 로그인 |
| POST | `/auth/refresh` | 토큰 갱신 |
| POST | `/auth/change-password` | 비밀번호 변경 |
| POST | `/auth/logout` | 로그아웃 |

### 포트폴리오 (16)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/portfolios` | 포트폴리오 목록 |
| POST | `/portfolios` | 포트폴리오 생성 |
| PATCH | `/portfolios/{id}` | 포트폴리오 수정 |
| DELETE | `/portfolios/{id}` | 포트폴리오 삭제 |
| GET | `/portfolios/{id}/holdings` | 보유종목 목록 |
| GET | `/portfolios/{id}/holdings/with-prices` | 보유종목 + 현재가 |
| POST | `/portfolios/{id}/holdings` | 보유종목 추가 |
| PATCH | `/portfolios/holdings/{hid}` | 보유종목 수정 |
| DELETE | `/portfolios/holdings/{hid}` | 보유종목 삭제 |
| GET | `/portfolios/{id}/transactions` | 거래내역 목록 |
| POST | `/portfolios/{id}/transactions` | 거래 기록 |
| DELETE | `/portfolios/transactions/{tid}` | 거래 삭제 |
| GET | `/portfolios/{id}/export/csv` | 보유종목 CSV 내보내기 |
| GET | `/portfolios/{id}/transactions/export/csv` | 거래내역 CSV 내보내기 |
| PATCH | `/portfolios/{id}/kis-account` | KIS 계좌 연결 |

### 대시보드 (1)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/dashboard/summary` | 대시보드 요약 |

### 분석 (4)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/analytics/metrics` | 수익률 지표 |
| GET | `/analytics/monthly-returns` | 월별 수익률 |
| GET | `/analytics/portfolio-history` | 포트폴리오 히스토리 |
| GET | `/analytics/sector-allocation` | 섹터별 배분 |

### 알림 (3)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/alerts` | 알림 목록 |
| POST | `/alerts` | 알림 생성 |
| DELETE | `/alerts/{id}` | 알림 삭제 |

### 종목 (2)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/stocks/search` | 종목 검색 |
| GET | `/stocks/{ticker}/detail` | 종목 상세 |

### 동기화 (3)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/sync/balance` | 전체 동기화 |
| POST | `/sync/{portfolio_id}` | 포트폴리오 동기화 |
| GET | `/sync/logs` | 동기화 로그 |

### KIS 계좌 관리 (5)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/users/kis-accounts` | KIS 계좌 등록 |
| GET | `/users/kis-accounts` | KIS 계좌 목록 |
| PATCH | `/users/kis-accounts/{id}` | KIS 계좌 수정 |
| DELETE | `/users/kis-accounts/{id}` | KIS 계좌 삭제 |
| POST | `/users/kis-accounts/{id}/test` | KIS 계좌 테스트 |

### 가격 (2)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/prices/{ticker}/history` | 가격 히스토리 |
| GET | `/prices/stream` | SSE 실시간 가격 스트림 |

### 차트 (1)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/chart/daily` | 일별 차트 데이터 |

### 관심종목 (3)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/watchlist` | 관심종목 목록 |
| POST | `/watchlist` | 관심종목 추가 |
| DELETE | `/watchlist/{id}` | 관심종목 삭제 |

### 헬스체크 (2)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 (루트) |
| GET | `/api/v1/health` | 서버 상태 확인 (버전) — DB, Redis, KIS API 상태 + last_backup_at |

### 내부 API (1)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/internal/backup-status` | DB 백업 결과 기록 (backup script에서 호출) |
