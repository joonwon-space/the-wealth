from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Priority: Authorization header (Bearer) > HttpOnly cookie
    token: Optional[str] = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_current_user_sse(
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """SSE 전용 인증 — 단기 티켓(sse-ticket:{uuid}) 우선, fallback으로 JWT token 허용.

    티켓 방식: POST /auth/sse-ticket으로 30초 TTL UUID 발급 → ?ticket= 파라미터로 전달.
    JWT 방식(레거시): ?token= 파라미터 (nginx 로그 노출 위험, 클라이언트 이전 후 제거 예정).
    """
    from app.core.config import settings  # noqa: PLC0415
    from app.core.redis_cache import get_redis_client  # noqa: PLC0415

    user_id: Optional[int] = None

    if ticket:
        # Ticket-based auth: single-use, 30s TTL
        async with get_redis_client(settings.REDIS_URL) as r:
            raw = await r.get(f"sse-ticket:{ticket}")
            if raw is not None:
                await r.delete(f"sse-ticket:{ticket}")
                try:
                    user_id = int(raw)
                except (ValueError, TypeError):
                    user_id = None
    elif token:
        # Legacy JWT fallback
        user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid SSE credentials")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
