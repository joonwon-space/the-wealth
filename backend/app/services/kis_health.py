"""KIS API 가용성 상태 관리.

앱 시작 시 KIS API 엔드포인트에 대한 연결 테스트를 수행하고
KIS_AVAILABLE 플래그를 설정한다.

가격 조회 서비스(kis_price.py)는 이 플래그를 확인해
KIS가 응답 불가 상태일 때 캐시 전용 모드로 동작한다.
"""

from dataclasses import dataclass, field

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# KIS 연결 테스트에 사용할 타임아웃(초)
_HEALTH_CHECK_TIMEOUT = 5.0


@dataclass
class KisAvailabilityState:
    """KIS API 가용성 상태."""

    is_available: bool = True
    last_error: str = field(default="")


# 앱 전역 KIS 가용성 상태 — 싱글톤 인스턴스
_state = KisAvailabilityState()


def get_kis_availability() -> bool:
    """현재 KIS API 가용성 플래그를 반환한다."""
    return _state.is_available


def set_kis_availability(available: bool, error: str = "") -> None:
    """KIS API 가용성 플래그를 설정한다 (테스트 및 내부 업데이트용)."""
    _state.is_available = available
    _state.last_error = error


async def check_kis_api_health() -> bool:
    """KIS API 연결 가능 여부를 확인한다.

    KIS 기본 URL에 HTTP HEAD 요청을 보내 연결 테스트를 수행한다.
    4xx/5xx 응답도 서버가 응답한 것이므로 가용 상태로 간주한다.
    네트워크 오류(타임아웃, 연결 거부 등)만 비가용 상태로 처리한다.

    반환값:
        True  — KIS API에 연결 가능
        False — 네트워크 오류로 연결 불가
    """
    url = settings.KIS_BASE_URL
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_CHECK_TIMEOUT) as client:
            # HEAD 요청은 응답 본문 없이 연결 가능 여부만 확인
            resp = await client.head(url)
            # 어떤 HTTP 상태 코드든 서버가 응답했으면 네트워크 레벨 가용
            logger.info(
                "[KisHealth] KIS API reachable — status=%d url=%s",
                resp.status_code,
                url,
            )
            set_kis_availability(True)
            return True
    except httpx.TimeoutException as exc:
        msg = f"Connection timed out after {_HEALTH_CHECK_TIMEOUT}s: {exc}"
        logger.warning("[KisHealth] KIS API unreachable — %s", msg)
        set_kis_availability(False, msg)
        return False
    except httpx.ConnectError as exc:
        msg = f"Connection refused or DNS failure: {exc}"
        logger.warning("[KisHealth] KIS API unreachable — %s", msg)
        set_kis_availability(False, msg)
        return False
    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        logger.warning("[KisHealth] KIS API health check failed — %s", msg)
        set_kis_availability(False, msg)
        return False
