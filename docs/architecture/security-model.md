# Security Model

위협 모델, 암호화 구현, 감사 로그, JWT 키 관리.

---

## 1. 위협 모델 (OWASP Top 10 대응)

| OWASP | 위협 | 현재 방어 |
|-------|------|----------|
| A01 Broken Access Control | IDOR — 다른 사용자의 데이터 접근 | 모든 protected 엔드포인트에서 `user_id` ownership 검증 |
| A02 Cryptographic Failures | KIS 자격증명 평문 저장 | AES-256-GCM 암호화 후 저장 (`app_key_enc`, `app_secret_enc`) |
| A03 Injection | SQL Injection | async SQLAlchemy ORM + parameterized queries |
| A05 Security Misconfiguration | 기본 시크릿 사용 | 기동 시 `ENCRYPTION_MASTER_KEY`, `JWT_SECRET_KEY` placeholder 검증 (`config.py:60-62`) |
| A07 Identification/Auth Failures | refresh token 탈취 | HttpOnly 쿠키, JTI rotation (one-time use), rate limit 20/min |
| A08 Software and Data Integrity | 변조된 JWT | HS256 서명 검증 (`JWT_SECRET_KEY`) |
| A09 Logging/Monitoring | 인증 이벤트 추적 불가 | `security_audit_logs` 테이블 (7가지 이벤트) |
| A10 SSRF | 내부 URL 조회 | KIS URL만 허용, 사용자 제공 URL 직접 호출 없음 |

---

## 2. AES-256-GCM 암호화

### 대상 필드

KIS 계좌 자격증명만 암호화 (`backend/app/models/kis_account.py:27-28`):

| 컬럼 | 타입 | 암호화 |
|------|------|--------|
| `app_key_enc` | `String(512)` | **Yes** — AES-256-GCM + base64 |
| `app_secret_enc` | `String(512)` | **Yes** — AES-256-GCM + base64 |
| `account_no` | `String(20)` | **No** — 평문 저장 |
| `acnt_prdt_cd` | `String(10)` | **No** — 평문 저장 |
| `label` | `String(100)` | **No** — 평문 저장 |

> `account_no`는 KIS 계좌번호로 내부 조회에 사용됨. 암호화되지 않음.

### 구현 (`backend/app/core/encryption.py`)

```python
# AES-256-GCM, 12바이트 nonce, 인증 태그 포함
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt(plaintext: str) -> str:
    aesgcm = AESGCM(_get_key())   # 32바이트 마스터 키
    nonce = os.urandom(12)        # 매 암호화마다 랜덤 nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt(token: str) -> str:
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(_get_key()).decrypt(nonce, ciphertext, None).decode()
```

마스터 키: `ENCRYPTION_MASTER_KEY` env var (64자 hex = 32바이트).
새 키 생성: `openssl rand -hex 32`

### 마스터 키 회전 절차

> 현재 키 회전을 위한 자동 마이그레이션 도구가 없음. 수동 절차:

```
1. 새 ENCRYPTION_MASTER_KEY 생성 (openssl rand -hex 32)
2. 모든 kis_accounts 레코드를 읽어 현재 키로 복호화
3. 새 키로 재암호화하여 저장
4. 서버 환경변수 업데이트 후 재시작
```

Python 예시 (관리자 스크립트로 실행):
```python
# 운영 DB에서 실행 — 충분한 백업 후 진행
from app.core.encryption import decrypt, encrypt
# OLD_KEY로 decrypt → NEW_KEY로 encrypt 후 DB UPDATE
```

**TODO: 키 회전 마이그레이션 스크립트 미구현** — 필요 시 수동 처리.

---

## 3. 비밀번호 해싱 (bcrypt)

`backend/app/core/security.py:19-24`:

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
```

- `bcrypt.gensalt()` 기본 cost factor: **12** (bcrypt 라이브러리 기본값)
- Salt는 해시 내에 포함되어 별도 저장 불필요
- 해시는 `users.hashed_password` 컬럼에 저장

---

## 4. JWT 서명 키

| 항목 | 값 |
|------|-----|
| 알고리즘 | `HS256` (`config.py:14`) |
| Access token 유효 기간 | 30분 (`ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Refresh token 유효 기간 | 7일 (`REFRESH_TOKEN_EXPIRE_DAYS`) |
| 서명 키 | `JWT_SECRET_KEY` env var (32바이트 랜덤 hex 권장) |

**키 회전 계획**: 현재 자동 키 회전 미구현. 키 노출 시 수동 절차:
1. 새 `JWT_SECRET_KEY` 생성
2. 서버 재시작 → 기존 토큰 전부 무효화
3. 모든 사용자 재로그인 필요 (refresh token Redis에서 자동 검증 실패)

Redis에서 모든 refresh JTI 삭제로 강제 로그아웃 가능:
```bash
redis-cli --scan --pattern "refresh:*" | xargs redis-cli del
```

---

## 5. security_audit_logs 추적 이벤트

`backend/app/models/security_audit_log.py:14-21` (`AuditAction` enum):

| Action | 트리거 |
|--------|--------|
| `LOGIN_SUCCESS` | `POST /auth/login` 성공 |
| `LOGIN_FAILURE` | `POST /auth/login` 비밀번호 불일치 |
| `LOGOUT` | `POST /auth/logout` |
| `PASSWORD_CHANGE` | `POST /users/me/change-password` |
| `ACCOUNT_DELETE` | `DELETE /users/me` |
| `KIS_CREDENTIAL_ADD` | KIS 계좌 연결 |
| `KIS_CREDENTIAL_DELETE` | KIS 계좌 삭제 |

**로그 필드**:
- `user_id` — 이벤트 주체 (계정 삭제 후 SET NULL)
- `action` — `AuditAction` enum
- `ip_address` — 클라이언트 IP (최대 45자, IPv6 지원)
- `user_agent` — 브라우저 UA
- `meta` — JSONB 추가 정보 (예: KIS_CREDENTIAL_ADD 시 `{account_no: "..."}`)

**주의**: audit log 기록 실패는 **무시**됨 (`audit_service.py:4` — "Errors are swallowed"). 감사 로그 누락이 사용자 요청을 실패시키지 않도록 설계.

보안 로그 조회 API: `GET /api/v1/users/me/security-logs`

---

## 6. 기타 보안 헤더

`backend/app/core/middleware.py`:

| 헤더 | 값 | 조건 |
|------|-----|------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | `ENVIRONMENT == 'production'` 시만 |
| `X-Content-Type-Options` | `nosniff` | 항상 |
| `X-Frame-Options` | `DENY` | 항상 |
| `Content-Security-Policy` | `default-src 'self' ...` | 항상 |

> CSP `'unsafe-inline'` 제거(nonce 도입)는 `SEC-105`로 미완료 상태 — `docs/plan/tasks.md` 참조.

---

## 7. Rate Limiting

전역 rate limit: `slowapi` 기반.

| 엔드포인트 그룹 | 제한 |
|----------------|------|
| `POST /auth/login` | 10/minute |
| `POST /auth/refresh` | 20/minute (SEC-101) |
| `POST /auth/register` | 5/minute |
| 주문 관련 (`/orders`) | 5회/분/user (app-level), 30/minute (endpoint-level, SEC-102) |
| `/orders/{id}/settle` | 10/minute (SEC-102) |

---

## Related

- [`docs/architecture/auth-flow.md`](./auth-flow.md) — JWT lifecycle, refresh token rotation, SSE ticket
- [`docs/architecture/database-schema.md`](./database-schema.md) — security_audit_logs 스키마
- [`docs/architecture/kis-integration.md`](./kis-integration.md) — KIS 자격증명 암호화 저장
