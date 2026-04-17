# Auth Flow Deep-Dive

JWT access + refresh + SSE ticket 전체 인증 흐름. 모든 수치는 소스에서 추출.

---

## 1. 토큰 유효 기간

| 토큰 | 기본 유효 기간 | 설정 변수 |
|------|--------------|----------|
| Access token (JWT) | **30분** | `ACCESS_TOKEN_EXPIRE_MINUTES` (`config.py:15`) |
| Refresh token (JWT) | **7일** | `REFRESH_TOKEN_EXPIRE_DAYS` (`config.py:16`) |
| SSE ticket (Redis) | **30초** | 하드코딩 (`auth.py:363`) |

---

## 2. 전체 인증 시퀀스 (ASCII)

```
Client                    Backend                     Redis
  │                         │                           │
  │  POST /auth/login        │                           │
  │  {email, password}       │                           │
  │─────────────────────────►│                           │
  │                         │  verify bcrypt hash        │
  │                         │  create_access_token()     │
  │                         │  create_refresh_token()    │
  │                         │  store_refresh_jti(jti)───►│ SET refresh:{uid}:{jti} TTL=7d
  │                         │                           │
  │◄─────────────────────────│ Set-Cookie: access_token (HttpOnly, 30min)
  │                         │ Set-Cookie: refresh_token (HttpOnly, 7d)
  │                         │ Set-Cookie: auth_status=1 (non-HttpOnly, 7d)
  │                         │                           │
  │                         │                           │
  │  API request (with cookie)                           │
  │─────────────────────────►│                           │
  │                         │  decode access_token       │
  │◄─────────────────────────│ 200 OK                    │
  │                         │                           │
  │  [access_token 만료 시]   │                           │
  │  API request → 401       │                           │
  │◄─────────────────────────│                           │
  │                         │                           │
  │  (Axios interceptor)     │                           │
  │  POST /auth/refresh      │                           │
  │─────────────────────────►│                           │
  │                         │  verify_and_consume_refresh_jti()
  │                         │──────────────────────────►│ GETDEL refresh:{uid}:{jti}
  │                         │◄──────────────────────────│ jti value
  │                         │  create new access_token   │
  │                         │  create new refresh_token  │
  │                         │  store_refresh_jti(new_jti)►│ SET refresh:{uid}:{new_jti}
  │◄─────────────────────────│ Set-Cookie: access_token (new)
  │                         │ Set-Cookie: refresh_token (new)
  │                         │                           │
  │  (원래 요청 재전송)        │                           │
  │─────────────────────────►│                           │
  │◄─────────────────────────│ 200 OK                    │
```

---

## 3. HttpOnly Cookie Dual-Write 이유

로그인/refresh 응답 시 **세 개의 쿠키** 동시 설정 (`auth.py:98-136`):

| 쿠키 | HttpOnly | 만료 | 목적 |
|------|----------|------|------|
| `access_token` | Yes | 30분 | JS에서 읽을 수 없어 XSS 보호 |
| `refresh_token` | Yes | 7일 | JS에서 읽을 수 없어 XSS 보호 |
| `auth_status=1` | **No** | 7일 | 클라이언트 로그인 상태 감지용 |

`auth_status`는 값이 없는 flag 쿠키. JS가 `document.cookie`에서 읽어 로그인 여부 확인.
`access_token`은 만료돼도 `refresh_token`이 살아있으면 interceptor가 자동 갱신 (`proxy.ts:15-19`).

쿠키 도메인: `COOKIE_DOMAIN` env var (예: `.joonwon.dev`). 서브도메인 간 공유를 위해 `.`으로 시작.

---

## 4. Axios 인터셉터 자동 갱신

`frontend/src/lib/api.ts:29-61`:

```typescript
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((p) => original?.url?.endsWith(p));

    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      try {
        // HttpOnly refresh_token 쿠키 자동 전송
        await axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true });
        return api(original);   // 원래 요청 재시도
      } catch {
        window.location.href = "/login";   // refresh도 실패 → 로그인 페이지
      }
    }
    // 401 외 에러: toast 알림
    if (error.response?.status !== 401) {
      toast.error(detail);
    }
    return Promise.reject(error);
  }
);
```

**동작 조건**:
- 401 응답이고
- `_retry` 플래그가 없고 (무한 루프 방지)
- Auth endpoint(`/auth/login`, `/auth/register`, `/auth/refresh`)가 아닌 경우

---

## 5. Redis Key 구조

`backend/app/core/security.py:16,53`:

```python
_REFRESH_TOKEN_PREFIX = "refresh:"
# 키 형식: f"{_REFRESH_TOKEN_PREFIX}{user_id}:{jti}"
# 예: "refresh:42:550e8400-e29b-41d4-a716-446655440000"
```

| Key 패턴 | TTL | 값 | 의미 |
|---------|-----|-----|------|
| `refresh:{user_id}:{jti}` | 7일 | `str(user_id)` | 유효한 refresh token JTI |
| `sse-ticket:{uuid}` | 30초 | `str(user_id)` | 1회용 SSE 연결 티켓 |

**Rotation**: `verify_and_consume_refresh_jti()`는 Redis에서 JTI를 읽고 **즉시 삭제** (one-time use). 새 JTI가 저장됨. 같은 refresh token으로 두 번 갱신 시도 → 두 번째는 실패.

---

## 6. SSE 티켓 흐름

SSE는 `EventSource`(브라우저 API)를 사용하며 HTTP 헤더 설정 불가. 따라서 Bearer token 대신 단기 티켓 사용.

```
Client                    Backend                     Redis
  │                         │                           │
  │  POST /auth/sse-ticket   │                           │
  │  (access_token cookie)   │                           │
  │─────────────────────────►│                           │
  │                         │  create UUID ticket        │
  │                         │──────────────────────────►│ SETEX sse-ticket:{uuid} 30 {user_id}
  │◄─────────────────────────│ {"ticket": "{uuid}"}      │
  │                         │                           │
  │  EventSource("/prices/stream?ticket={uuid}")         │
  │─────────────────────────►│                           │
  │                         │  get_current_user_sse()    │
  │                         │──────────────────────────►│ GET sse-ticket:{uuid}
  │                         │◄──────────────────────────│ user_id
  │                         │──────────────────────────►│ DEL sse-ticket:{uuid}  (1회용)
  │◄═════════════════════════│ SSE stream (text/event-stream)
```

구현: `backend/app/api/auth.py:356-363`, `backend/app/api/deps.py:56-68`

레거시 `?token=` URL 파라미터 방식은 **보안 취약(nginx access log 노출)** 으로 제거됨 (SEC-103).

---

## 7. 세션 목록 / Revoke 플로우

### 세션 목록 조회

`GET /auth/sessions` (`auth.py:312-336`):
- Redis에서 `refresh:{user_id}:*` 패턴 SCAN
- 각 JTI의 생성 시각 파싱 후 `SessionInfo` 목록 반환

### 단일 세션 Revoke

`DELETE /auth/sessions/{jti}` (`auth.py:339-...`):
- `refresh:{user_id}:{jti}` Redis 키 삭제
- 해당 device/session만 로그아웃

### 전체 세션 Revoke (로그아웃)

`POST /auth/logout` (`auth.py:288-301`):
```python
await revoke_all_refresh_tokens_for_user(current_user.id)
```
`refresh:{user_id}:*` 패턴의 모든 키 삭제 (SCAN + DEL). 쿠키도 삭제.

### 비밀번호 변경 시

`POST /users/me/change-password` — 변경 후 `revoke_all_refresh_tokens_for_user()` 호출. 모든 기기 로그아웃.

---

## Related

- [`docs/architecture/security-model.md`](./security-model.md) — bcrypt, JWT 서명 키 회전, AES-256
- [`docs/architecture/kis-integration.md`](./kis-integration.md) — KIS 토큰과 JWT 인증의 분리
- [`docs/runbooks/troubleshooting.md`](../runbooks/troubleshooting.md) — SSE 연결 실패 해결
