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
| 테스트 | 기본 구축 | Backend 36개 + Frontend 14개 = 총 50개 테스트 (pytest + vitest) |
| 배포 | 미완 | Dockerfile 존재, 실제 배포 미수행 |

### 강점

- **전체 수직 통합**: 인증 → 포트폴리오 → 종목 → 현재가 → 수익률까지 한 번에 동작
- **보안 설계**: AES-256 암호화, IDOR 방지, JWT rotation, rate limiting
- **실시간 계산**: 현재가를 DB에 저장하지 않고 API 호출로 동적 계산 (stale data 방지)
- **자동 동기화**: APScheduler로 KIS 계좌 자동 reconciliation
- **종목 검색**: KRX + Naver ETF 합산 3,695개 종목 로컬 검색 (Redis 캐싱)

### 약점

- ~~테스트 부재~~ → **해결**: pytest(36개) + vitest(14개) = 총 50개 테스트
- ~~에러 UX~~ → **해결**: sonner toast + error boundary + 대시보드 에러 UI 추가
- ~~shadcn/ui 컴포넌트 부족~~ → **해결**: Dialog, Input, Card, Table, Skeleton, Sonner 설치
- ~~모바일 대응 부재~~ → **해결**: 햄버거 메뉴 + 반응형 사이드바 (md breakpoint)
- **해외주식 검색 미지원**: 현재가 조회는 가능하나 해외 종목 검색 불가
- **거래 이력(transactions) 미활용**: 모델만 존재, API/UI 없음
- **분석 페이지 미구현**: placeholder 페이지만 있음, 실제 차트/분석 미구현
- ~~자동 동기화 미완성~~ → **해결**: `_sync_all_accounts()` DB 사용자 조회 + reconciliation 구현
- ~~Python 의존성 취약점~~ → **일부 해결**: setuptools 업그레이드, python-multipart는 Python 3.10+ 필요 (todo.md에 추가)
- ~~ruff 미설치~~ → **해결**: ruff 설치 + 4개 lint 에러 수정

---

## 2. 기술적 리스크

### 높음

| 리스크 | 설명 | 완화 방안 |
|--------|------|-----------|
| **KRX KIND 스크래핑 불안정** | HTML 구조 변경 시 파싱 실패 | KRX 공식 API 전환 또는 폴백 로직 추가 |
| **Naver Finance API 비공식** | 공식 API 아님, 차단/변경 가능 | KRX 데이터 포털 또는 자체 ETF DB 구축 |
| ~~KIS API 장애 시 대시보드 먹통~~ | **해결**: Redis 가격 캐시 폴백(TTL 1h) + 에러 UI 추가 | — |
| ~~테스트 없음~~ | **해결**: pytest 29개 + vitest 9개 테스트 구축 | — |

### 중간

| 리스크 | 설명 | 완화 방안 |
|--------|------|-----------|
| **Redis 단일 장애점** | Redis 다운 시 토큰/검색 불가 | Redis 없을 때 in-memory 폴백 |
| **bcrypt 버전 호환** | ~~bcrypt 5.x ↔ passlib 호환 이슈~~ | **해결됨** — bcrypt 5.0.0 + passlib 정상 동작 확인 (2026-03-16) |
| **Python 3.9 호환** | `str | None` 대신 `Optional[str]` 사용 필요 | `from __future__ import annotations` 적용 완료 |
| **Python 의존성 CVE** | python-multipart, setuptools, ecdsa 취약점 | pip-audit 결과 10개 — 업그레이드 필요 |

---

## 3. 개선 기회 (우선순위순)

### P0 — ~~즉시 필요~~ 해결됨

1. ~~테스트 인프라 구축~~ → **완료**: pytest 29개 + vitest 9개
2. ~~에러 핸들링 강화~~ → **완료**: sonner toast + error boundary + 대시보드 에러 UI

### P1 — ~~단기 개선~~ 해결됨

3. ~~shadcn/ui 컴포넌트 정리~~ → **완료**: Dialog, Input, Card, Table, Skeleton, Sonner 설치
4. ~~모바일 반응형~~ → **완료**: 햄버거 메뉴 + 반응형 사이드바
5. ~~현재가 캐싱 폴백~~ → **완료**: Redis 가격 캐시(TTL 1h) + 서버 시작 시 프리로딩

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
| ~~첫 검색 지연~~ | **해결**: 서버 startup lifespan에서 프리로딩 | — |

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
| XSS | OK | React 기본 이스케이핑, dangerouslySetInnerHTML 미사용 확인 완료 |
| CSRF | OK | cookie에 `SameSite=Lax` 설정 확인 완료 (2026-03-16) |
| Secret rotation | 미흡 | 키 rotation 메커니즘 없음 |
