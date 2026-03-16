# THE WEALTH — Project Analysis

## 목적

프로젝트의 기술적 강점, 약점, 개선 기회, 리스크를 분석한다.
`project-overview.md`가 "무엇이 있는가"라면, 이 문서는 "무엇이 부족하고 어디로 가야 하는가"를 다룬다.

---

## 1. 현재 상태 평가

### 완성도

| 영역 | 상태 | 비고 |
|------|------|------|
| 백엔드 API | 완료 | 인증, CRUD, 동기화, 검색 전부 동작 |
| DB 스키마 | 완료 | 5개 테이블, 3개 마이그레이션 |
| 프론트엔드 UI | 완료 (기본) | 모든 페이지 존재, 기본 CRUD 동작 |
| KIS 연동 | 완료 | 토큰, 현재가, 계좌 잔고, 자동 동기화 |
| 테스트 | 미흡 | 테스트 코드 부재 — TDD 규칙 대비 미충족 |
| 배포 | 미완 | Dockerfile 존재, 실제 배포 미수행 |

### 강점

- **전체 수직 통합**: 인증 → 포트폴리오 → 종목 → 현재가 → 수익률까지 한 번에 동작
- **보안 설계**: AES-256 암호화, IDOR 방지, JWT rotation, rate limiting
- **실시간 계산**: 현재가를 DB에 저장하지 않고 API 호출로 동적 계산 (stale data 방지)
- **자동 동기화**: APScheduler로 KIS 계좌 자동 reconciliation
- **종목 검색**: KRX + Naver ETF 합산 3,695개 종목 로컬 검색 (Redis 캐싱)

### 약점

- **테스트 부재**: 단위/통합/E2E 테스트 없음 — CLAUDE.md의 "80%+ 커버리지" 규칙 미충족
- **에러 UX**: API 에러 시 프론트엔드 사용자 피드백 부족 (toast/snackbar 미구현 영역 있음)
- **shadcn/ui 컴포넌트 부족**: button만 설치, dialog/input/card 등 미설치 (인라인 HTML로 대체)
- **모바일 대응 부재**: 사이드바 고정 60px, 모바일 반응형 미구현
- **해외주식 검색 미지원**: 현재가 조회는 가능하나 해외 종목 검색 불가
- **거래 이력(transactions) 미활용**: 모델만 존재, API/UI 없음
- **분석 페이지 미구현**: 사이드바에 "분석" 메뉴 있으나 페이지 없음

---

## 2. 기술적 리스크

### 높음

| 리스크 | 설명 | 완화 방안 |
|--------|------|-----------|
| **KRX KIND 스크래핑 불안정** | HTML 구조 변경 시 파싱 실패 | KRX 공식 API 전환 또는 폴백 로직 추가 |
| **Naver Finance API 비공식** | 공식 API 아님, 차단/변경 가능 | KRX 데이터 포털 또는 자체 ETF DB 구축 |
| **KIS API 장애 시 대시보드 먹통** | 현재가를 100% KIS에 의존 | 마지막 조회 가격 캐싱, 가격 조회 실패 시 캐시 폴백 |
| **테스트 없음** | 리팩토링/기능 추가 시 회귀 버그 위험 | pytest + vitest 도입 우선순위 높음 |

### 중간

| 리스크 | 설명 | 완화 방안 |
|--------|------|-----------|
| **Redis 단일 장애점** | Redis 다운 시 토큰/검색 불가 | Redis 없을 때 in-memory 폴백 |
| **bcrypt 버전 호환** | bcrypt 5.x ↔ passlib 호환 이슈 발생 이력 | bcrypt==4.0.1 고정 (현재 5.0.0 — 재확인 필요) |
| **Python 3.9 호환** | `str | None` 대신 `Optional[str]` 사용 필요 | `from __future__ import annotations` 적용 완료 |

---

## 3. 개선 기회 (우선순위순)

### P0 — 즉시 필요

1. **테스트 인프라 구축**
   - Backend: pytest + pytest-asyncio, 핵심 서비스/API 단위 테스트
   - Frontend: vitest + React Testing Library, 컴포넌트/훅 테스트
   - 목표: 핵심 경로(인증, CRUD, 동기화) 80%+ 커버리지

2. **에러 핸들링 강화**
   - 프론트엔드 전역 에러 바운더리
   - API 에러 시 사용자 친화적 toast 알림 통합
   - 네트워크 오류 시 재시도/오프라인 표시

### P1 — 단기 개선

3. **shadcn/ui 컴포넌트 정리**
   - Dialog, Input, Card, Table 등 설치하여 인라인 HTML 교체
   - 일관된 디자인 시스템 확보

4. **모바일 반응형**
   - 사이드바 → 바텀 네비게이션 또는 햄버거 메뉴
   - 대시보드 카드 스택 레이아웃

5. **현재가 캐싱 폴백**
   - Redis에 마지막 조회 가격 저장 (TTL 1h)
   - KIS API 실패 시 캐시 가격 + "마지막 업데이트: N분 전" 표시

### P2 — 중기 기능

6. **거래 이력 활용**
   - 매매 기록 API + UI
   - 수익률 시계열 차트 (일별/월별)

7. **분석 페이지 구현**
   - 포트폴리오 성과 분석
   - 섹터/자산군별 배분
   - 벤치마크(KOSPI200) 대비 성과

8. **해외주식 검색**
   - US 주요 종목 DB 또는 외부 API 연동
   - 환율 반영 수익률 계산

### P3 — 장기 비전

9. **배포 파이프라인**
   - Vercel (프론트엔드) + Railway/Fly.io (백엔드)
   - CI/CD (GitHub Actions): lint → test → build → deploy

10. **알림 시스템**
    - 목표가 도달 알림
    - 일일 포트폴리오 리포트

---

## 4. 성능 병목점

| 지점 | 현재 상태 | 개선 방향 |
|------|-----------|-----------|
| **종목 검색** | 3,695개 리스트 전체 순회 (`O(n)`) | 초성 검색, trie 구조, 또는 Redis SCAN |
| **현재가 조회** | `asyncio.gather`로 종목별 KIS API 호출 | 종목 수 많으면 rate limit 위험 — 배치 API 탐색 |
| **대시보드 로딩** | 30초 interval polling | WebSocket 또는 SSE로 push 방식 전환 |
| **첫 검색 지연** | KRX + Naver fetch에 10-15초 | 서버 시작 시 백그라운드 프리로딩 |

---

## 5. 보안 점검

| 항목 | 상태 | 비고 |
|------|------|------|
| JWT 토큰 만료 | OK | access 30min, refresh 7d |
| 비밀번호 해싱 | OK | bcrypt |
| KIS 키 암호화 | OK | AES-256-GCM, 마스터키 환경변수 |
| IDOR 방지 | OK | user_id 소유권 검증 |
| SQL Injection | OK | SQLAlchemy ORM 사용 |
| Rate Limiting | OK | slowapi 60 req/min |
| CORS | OK | localhost:3000만 허용 |
| XSS | 주의 | React 기본 이스케이핑에 의존, dangerouslySetInnerHTML 미사용 확인 필요 |
| CSRF | 미흡 | JWT Bearer 방식이라 CSRF 토큰 불필요하나, cookie 기반이면 SameSite 확인 필요 |
| Secret rotation | 미흡 | 키 rotation 메커니즘 없음 |
