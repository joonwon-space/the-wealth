# THE WEALTH — 인프라 구성도

## 1. 전체 아키텍처

```
                         ┌─────────────────────────────────┐
                         │         Cloudflare Network       │
                         │                                  │
                         │   ┌──── DNS ────────────────┐    │
                         │   │  joonwon.dev     → CNAME │    │
                         │   │  api.joonwon.dev → CNAME │    │
                         │   └─────────────────────────┘    │
                         │                                  │
   [사용자 브라우저] ─────▶│   ┌──── TLS 종단 ────────────┐   │
        HTTPS             │   │  Cloudflare Edge           │   │
                         │   │  - SSL/TLS 자동 인증서      │   │
                         │   │  - DDoS 방어               │   │
                         │   │  - CDN 캐싱 (정적 자산)     │   │
                         │   └──────────┬──────────────┘   │
                         └──────────────┼──────────────────┘
                                        │
                              Cloudflare Tunnel
                              (암호화된 아웃바운드 연결)
                              포트 포워딩 불필요
                                        │
                         ┌──────────────┼──────────────────┐
                         │          로컬 서버 (macOS)       │
                         │              │                   │
                         │    ┌─────────┴─────────┐        │
                         │    │    cloudflared     │        │
                         │    │   (launchd 서비스)  │        │
                         │    └────┬──────────┬───┘        │
                         │         │          │             │
                         │   ┌─────┴──┐  ┌───┴──────┐     │
                         │   │ :3000  │  │  :8000   │     │
                         │   │Frontend│  │ Backend  │     │
                         │   └────────┘  └────┬─────┘     │
                         │                     │           │
                         │              ┌──────┴──────┐    │
                         │              │             │    │
                         │         ┌────┴───┐  ┌─────┴─┐  │
                         │         │ :5432  │  │ :6379 │  │
                         │         │Postgres│  │ Redis │  │
                         │         └────────┘  └───────┘  │
                         │                                 │
                         │      Docker Compose 관리         │
                         └─────────────────────────────────┘
```

## 2. 네트워크 흐름

### 프론트엔드 페이지 요청
```
브라우저 → https://joonwon.dev
       → Cloudflare Edge (TLS 종단)
       → Cloudflare Tunnel
       → cloudflared (로컬)
       → localhost:3000 (Next.js standalone)
       → HTML/JS/CSS 응답
```

### API 호출
```
브라우저 → https://api.joonwon.dev/dashboard/summary
       → Cloudflare Edge (TLS 종단, CORS preflight 통과)
       → Cloudflare Tunnel
       → cloudflared (로컬)
       → localhost:8000 (FastAPI)
       → PostgreSQL / Redis / KIS API
       → JSON 응답
```

### KIS API 호출 (백엔드 → 외부)
```
FastAPI → https://openapi.koreainvestment.com
       → KIS 인증 토큰 (Redis 캐시, 24시간 TTL)
       → 현재가 / 잔고 / 종목 정보 조회
```

## 3. 서비스 상세

### 3-1. Cloudflare Tunnel (`cloudflared`)

| 항목 | 값 |
|------|-----|
| 터널 ID | `ab0b0efa-0623-4ca4-8a8d-526dec26cf6a` |
| 설정 파일 | `~/.cloudflared/config.yml` |
| 인증 파일 | `~/.cloudflared/<tunnel-id>.json` |
| 실행 방식 | macOS launchd (사용자 로그인 시 자동 시작) |
| 로그 | `~/Library/Logs/com.cloudflare.cloudflared.*.log` |

**Ingress 규칙:**
```yaml
ingress:
  - hostname: api.joonwon.dev  → http://localhost:8000
  - hostname: joonwon.dev      → http://localhost:3000
  - service: http_status:404   # catch-all
```

### 3-2. Frontend (Next.js)

| 항목 | 값 |
|------|-----|
| 프레임워크 | Next.js 16 (App Router, React 19) |
| 빌드 모드 | `output: "standalone"` (프로덕션 빌드) |
| 포트 | 3000 |
| API 엔드포인트 | `NEXT_PUBLIC_API_URL=https://api.joonwon.dev` |
| 이미지 | `node:20-alpine` (멀티스테이지 빌드) |
| UI 라이브러리 | shadcn/ui (base-nova, neutral) |
| 차트 | Recharts (도넛, 라인, 바, 캔들스틱) |
| 테이블 | TanStack Table v8 |

### 3-3. Backend (FastAPI)

| 항목 | 값 |
|------|-----|
| 프레임워크 | FastAPI + Uvicorn |
| 포트 | 8000 |
| ORM | SQLAlchemy 2.x (async) |
| 마이그레이션 | Alembic |
| 인증 | JWT (PyJWT) + bcrypt |
| 스케줄러 | APScheduler (장 마감 스냅샷, KST 16:05) |
| KIS 토큰 | Redis 캐시 (24시간 TTL, 만료 전 자동 갱신) |
| 암호화 | AES-256 (KIS 자격증명) |
| Rate Limit | slowapi (60 req/min) |
| 이미지 | Python 3.12 slim (멀티스테이지 빌드) |

### 3-4. PostgreSQL

| 항목 | 값 |
|------|-----|
| 버전 | 16-alpine |
| 포트 | 5432 |
| DB 이름 | `the_wealth` |
| 데이터 영속성 | Docker named volume (`postgres_data`) |
| 주요 테이블 | `users`, `portfolios`, `holdings`, `transactions`, `kis_accounts`, `price_snapshots`, `alerts` |

### 3-5. Redis

| 항목 | 값 |
|------|-----|
| 버전 | 7-alpine |
| 포트 | 6379 |
| 데이터 영속성 | Docker named volume (`redis_data`) |
| 용도 | KIS 토큰 캐시, 종목 가격 캐시 (5분 TTL), 종목 검색 목록 |

## 4. 도메인 & DNS 구성

```
joonwon.dev
├── @  (root)  → CNAME → <tunnel-id>.cfargotunnel.com   (프론트엔드)
└── api        → CNAME → <tunnel-id>.cfargotunnel.com   (백엔드 API)
```

- 네임서버: Cloudflare (Registrar에서 구매 → 자동 설정)
- SSL: Cloudflare Edge에서 자동 발급 (Universal SSL)
- Proxy 상태: Proxied (오렌지 클라우드) — DDoS 방어, CDN 활성

## 5. 데이터 영속성 & 백업

### Docker Named Volumes
```
postgres_data  →  /var/lib/docker/volumes/the-wealth_postgres_data/_data
redis_data     →  /var/lib/docker/volumes/the-wealth_redis_data/_data
```

- `docker-compose down` → 데이터 유지 ✅
- `docker-compose down -v` → 데이터 삭제 ⚠️ (`-v` 플래그 주의)
- 시스템 재시작 → 데이터 유지 ✅

### 백업 전략 (권장)
```bash
# 일일 자동 백업 (cron)
0 3 * * * docker exec the-wealth-postgres-1 pg_dump -U postgres the_wealth | gzip > ~/backups/db_$(date +\%Y\%m\%d).sql.gz

# 수동 백업
docker exec the-wealth-postgres-1 pg_dump -U postgres the_wealth > backup.sql

# 복원
cat backup.sql | docker exec -i the-wealth-postgres-1 psql -U postgres the_wealth
```

## 6. 시스템 시작 순서

```
macOS 부팅 / 사용자 로그인
    │
    ├── 1. Docker Desktop (자동 시작 설정)
    │     └── docker-compose services
    │           ├── postgres  (healthcheck: pg_isready)
    │           ├── redis     (healthcheck: redis-cli ping)
    │           ├── backend   (depends_on: postgres✅, redis✅)
    │           └── frontend  (depends_on: backend✅)
    │
    └── 2. cloudflared (launchd user agent)
          └── tunnel "the-wealth"
                ├── joonwon.dev     → :3000
                └── api.joonwon.dev → :8000
```

### Docker Desktop 자동 시작
`Docker Desktop → Settings → General → ✅ Start Docker Desktop when you sign in`

### Docker Compose 자동 재시작
`docker-compose.yml`에 `restart: unless-stopped` 추가 권장:
```yaml
services:
  postgres:
    restart: unless-stopped
  redis:
    restart: unless-stopped
  backend:
    restart: unless-stopped
  frontend:
    restart: unless-stopped
```

## 7. 보안 구성

| 계층 | 보호 수단 |
|------|----------|
| 네트워크 | Cloudflare Tunnel (인바운드 포트 개방 불필요) |
| TLS | Cloudflare Edge Universal SSL (자동 갱신) |
| DDoS | Cloudflare 기본 방어 (무료 플랜 포함) |
| CORS | `CORS_ORIGINS=http://localhost:3000,https://joonwon.dev` |
| 인증 | JWT access token (30분) + refresh token rotation (7일) |
| 비밀번호 | bcrypt (salt rounds: 12) |
| KIS 자격증명 | AES-256 암호화 (마스터 키: 환경변수) |
| Rate Limit | 60 req/min per IP (slowapi) |
| IDOR 방지 | 모든 API에서 user_id 소유권 검증 |

### 포트 노출 현황
```
외부 노출: 없음 (Cloudflare Tunnel이 아웃바운드 연결)
로컬 노출: 3000, 5432, 6379, 8000 (Docker → localhost only)
```

## 8. 모니터링 (현재 상태)

| 항목 | 방법 |
|------|------|
| 터널 상태 | `cloudflared tunnel info the-wealth` |
| 컨테이너 상태 | `docker-compose ps` |
| 백엔드 헬스 | `curl https://api.joonwon.dev/health` |
| 로그 확인 | `docker-compose logs -f <서비스명>` |
| 터널 로그 | `tail -f ~/Library/Logs/com.cloudflare.cloudflared.err.log` |

## 9. 운영 명령어 치트시트

```bash
# --- Docker Compose ---
docker-compose up -d                  # 전체 시작
docker-compose up -d --build          # 재빌드 후 시작
docker-compose down                   # 전체 중지 (데이터 유지)
docker-compose restart backend        # 백엔드만 재시작
docker-compose logs -f backend        # 백엔드 로그 실시간

# --- Cloudflare Tunnel ---
cloudflared tunnel info the-wealth    # 터널 상태
cloudflared tunnel run the-wealth     # 수동 실행 (디버깅용)
launchctl list | grep cloudflare      # launchd 서비스 상태

# --- 데이터베이스 ---
docker exec -it the-wealth-postgres-1 psql -U postgres the_wealth   # DB 접속
docker exec the-wealth-postgres-1 pg_dump -U postgres the_wealth > backup.sql  # 백업

# --- 업데이트 배포 ---
cd ~/Documents/GitHub/the-wealth
git pull
docker-compose up -d --build          # 코드 변경 후 재빌드
```
