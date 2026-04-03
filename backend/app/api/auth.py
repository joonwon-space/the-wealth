from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    list_sessions_for_user,
    revoke_all_refresh_tokens_for_user,
    revoke_session_for_user,
    store_refresh_jti,
    verify_and_consume_refresh_jti,
    verify_password,
)
from app.api.deps import get_current_user
from app.db.session import AsyncSessionLocal, get_db
from app.models.security_audit_log import AuditAction
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SessionItem,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import log_event

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


async def _bg_sync_user(user_id: int) -> None:
    """로그인 후 백그라운드에서 KIS 계좌 자동 동기화.

    로그인 응답 반환 후 비동기로 실행되므로 로그인 지연 없음.
    """
    # Lazy imports to avoid circular dependency
    from app.api.sync import _ensure_portfolio_for_account, _fetch_balance_raw  # noqa: PLC0415
    from app.models.kis_account import KisAccount  # noqa: PLC0415
    from app.models.sync_log import SyncLog  # noqa: PLC0415
    from app.services.reconciliation import reconcile_holdings  # noqa: PLC0415

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(KisAccount).where(KisAccount.user_id == user_id)
            )
            accounts = list(result.scalars().all())
            if not accounts:
                return

            for acct in accounts:
                try:
                    _, kis_holdings = await _fetch_balance_raw(acct)
                    portfolio = await _ensure_portfolio_for_account(db, user_id, acct)
                    counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
                    log = SyncLog(
                        user_id=user_id,
                        portfolio_id=portfolio.id,
                        status="success",
                        inserted=counts["inserted"],
                        updated=counts["updated"],
                        deleted=counts["deleted"],
                        message="login-sync",
                    )
                    db.add(log)
                    await db.commit()
                    logger.info(
                        "Login sync user=%d %s: +%d ~%d -%d",
                        user_id,
                        acct.label,
                        counts["inserted"],
                        counts["updated"],
                        counts["deleted"],
                    )
                except Exception as exc:
                    logger.warning("Login sync failed user=%d acct=%s: %s", user_id, acct.label, exc)
    except Exception as exc:
        logger.warning("Login sync DB error user=%d: %s", user_id, exc)

# Cookie settings
_ACCESS_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
# Secure flag: off when CORS origins include localhost (local dev via HTTP)
_SECURE_COOKIE = "localhost" not in settings.CORS_ORIGINS
# Domain: set to e.g. ".joonwon.dev" so both joonwon.dev and api.joonwon.dev share cookies
_COOKIE_DOMAIN = settings.COOKIE_DOMAIN or None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly auth cookies on the response.

    Also sets a non-HttpOnly `auth_status=1` flag cookie so the client can
    detect login state without reading the HttpOnly token.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=_ACCESS_MAX_AGE,
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=_REFRESH_MAX_AGE,
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/",
        domain=_COOKIE_DOMAIN,
    )
    # Non-HttpOnly flag for client-side auth state detection.
    # Lifetime matches refresh_token so the client stays aware of login state
    # for the full 7-day session (access_token silently refreshes on expiry).
    response.set_cookie(
        key="auth_status",
        value="1",
        max_age=_REFRESH_MAX_AGE,
        httponly=False,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/",
        domain=_COOKIE_DOMAIN,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout.

    Deletes cookies both with and without domain to handle domain-mismatch
    edge cases where the cookie was set without a domain or with a different
    domain than _COOKIE_DOMAIN.
    """
    for cookie_name in ("access_token", "refresh_token", "auth_status"):
        response.delete_cookie(key=cookie_name, path="/", domain=_COOKIE_DOMAIN)
        if _COOKIE_DOMAIN is not None:
            # Also delete without domain in case the cookie was stored without one
            response.delete_cookie(key=cookie_name, path="/", domain=None)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed"
        )

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        failed_user_id = user.id if user is not None else None
        await log_event(
            db,
            AuditAction.LOGIN_FAILURE,
            user_id=failed_user_id,
            request=request,
            meta={"email": body.email},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(user.id)
    refresh_token, jti = create_refresh_token(user.id)
    await store_refresh_jti(jti, user.id)
    await log_event(db, AuditAction.LOGIN_SUCCESS, user_id=user.id, request=request)
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token)

    # 로그인 후 백그라운드에서 KIS 계좌 자동 동기화 (응답 지연 없음)
    background_tasks.add_task(_bg_sync_user, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Accept refresh token from JSON body or HttpOnly cookie
    token_str = body.refresh_token or request.cookies.get("refresh_token")
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    decoded = decode_refresh_token(token_str)
    if decoded is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify jti exists in Redis and consume it (one-time use)
    jti_valid = await verify_and_consume_refresh_jti(decoded["jti"], decoded["user_id"])
    if not jti_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used or revoked",
        )

    result = await db.execute(select(User).where(User.id == decoded["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Issue new refresh token (rotation)
    new_access_token = create_access_token(user.id)
    new_refresh_token, new_jti = create_refresh_token(user.id)
    await store_refresh_jti(new_jti, user.id)

    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password", status_code=204)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change password and revoke all existing refresh tokens."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )
    current_user.hashed_password = hash_password(body.new_password)
    await log_event(db, AuditAction.PASSWORD_CHANGE, user_id=current_user.id, request=request)
    await db.commit()
    await revoke_all_refresh_tokens_for_user(current_user.id)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke all refresh tokens and clear auth cookies."""
    await revoke_all_refresh_tokens_for_user(current_user.id)
    await log_event(db, AuditAction.LOGOUT, user_id=current_user.id, request=request)
    await db.commit()
    _clear_auth_cookies(response)


@router.get("/sessions", response_model=list[SessionItem])
@limiter.limit("30/minute")
async def get_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> list[SessionItem]:
    """현재 사용자의 활성 세션 목록 조회.

    Redis에 저장된 refresh:{user_id}:* 키를 스캔해 세션 목록을 반환한다.
    현재 요청에 사용된 JTI를 is_current=True로 표시한다.
    """
    # 현재 요청 토큰에서 JTI 추출 (쿠키 또는 Authorization 헤더)
    current_jti: Optional[str] = None
    raw_token = request.cookies.get("access_token") or ""
    if not raw_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
    if raw_token:
        try:
            import jwt as _jwt  # noqa: PLC0415
            from app.core.config import settings as _s  # noqa: PLC0415
            payload = _jwt.decode(raw_token, _s.JWT_SECRET_KEY, algorithms=[_s.JWT_ALGORITHM])
            current_jti = payload.get("jti")
        except Exception:
            pass

    sessions = await list_sessions_for_user(current_user.id)
    return [
        SessionItem(
            jti=s["jti"],
            created_at=s.get("created_at"),
            is_current=(s["jti"] == current_jti),
        )
        for s in sessions
    ]


@router.delete("/sessions/{jti}", status_code=204)
@limiter.limit("30/minute")
async def revoke_session(
    request: Request,
    jti: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """특정 세션 revoke (개별 기기 로그아웃).

    jti가 현재 사용자 소유인지 확인 후 Redis에서 삭제한다.
    존재하지 않는 JTI는 404를 반환한다.
    """
    deleted = await revoke_session_for_user(current_user.id, jti)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
