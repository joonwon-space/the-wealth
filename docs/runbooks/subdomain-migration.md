# 서브도메인 전환 플랜

`joonwon.dev` → `the-wealth.joonwon.dev`

## 도메인 변경 목표

| 컴포넌트 | 현재 | 목표 |
|---------|------|------|
| Frontend | `https://joonwon.dev` | `https://the-wealth.joonwon.dev` |
| Backend API | `https://api.joonwon.dev` | `https://api.the-wealth.joonwon.dev` |

---

## 1단계: DNS 설정

도메인 registrar 또는 Cloudflare에서 추가:

```
the-wealth.joonwon.dev       CNAME → joonwon.dev  (또는 서버 IP A 레코드)
api.the-wealth.joonwon.dev   CNAME → joonwon.dev  (또는 서버 IP A 레코드)
```

---

## 2단계: 서버 리버스 프록시 설정

이 repo 밖에서 관리되는 서버 리버스 프록시를 업데이트한다.

**Caddy (`Caddyfile`):**
```
the-wealth.joonwon.dev {
    reverse_proxy localhost:3000
}

api.the-wealth.joonwon.dev {
    reverse_proxy localhost:8000
}
```

**Nginx (새 server block 추가):**
기존 `joonwon.dev` 블록을 복사하고 `server_name`을 새 도메인으로 변경한다.

---

## 3단계: 코드 변경 (`docker-compose.yml`, `.env.example`)

### `docker-compose.yml`

```yaml
# Before
NEXT_PUBLIC_API_URL: https://api.joonwon.dev
CORS_ORIGINS: http://localhost:3000,https://joonwon.dev

# After
NEXT_PUBLIC_API_URL: https://api.the-wealth.joonwon.dev
CORS_ORIGINS: http://localhost:3000,https://the-wealth.joonwon.dev
```

### `backend/.env.example`

```
# Before
CORS_ORIGINS=http://localhost:3000,https://joonwon.dev

# After
CORS_ORIGINS=http://localhost:3000,https://the-wealth.joonwon.dev
```

> `COOKIE_DOMAIN=.joonwon.dev`는 서브도메인에도 적용되므로 변경 불필요.

---

## 4단계: GitHub Secrets 업데이트

GitHub repo → **Settings → Secrets and variables → Actions** 에서
`BACKEND_ENV` 시크릿 내 `CORS_ORIGINS` 값을 새 URL로 변경한다.

---

## 5단계: 배포 및 검증

```bash
# main 브랜치 push → GitHub Actions 자동 배포
# 또는 서버에서 직접:
docker compose build --parallel
docker compose up -d --remove-orphans
```

헬스체크 확인:
```bash
curl https://api.the-wealth.joonwon.dev/api/v1/health
curl https://the-wealth.joonwon.dev
```

---

## 6단계: 모니터링 업데이트

- **UptimeRobot**: 헬스체크 URL을 `https://api.the-wealth.joonwon.dev/api/v1/health`로 변경

---

## 7단계: 기존 도메인 처리 (선택)

`joonwon.dev`에 다른 프로젝트 예정이라면 리다이렉트 설정:

**Caddy:**
```
joonwon.dev {
    redir https://the-wealth.joonwon.dev{uri} 301
}
```

**Nginx:**
```nginx
server {
    server_name joonwon.dev;
    return 301 https://the-wealth.joonwon.dev$request_uri;
}
```
