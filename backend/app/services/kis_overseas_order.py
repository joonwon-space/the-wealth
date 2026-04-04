"""해외주식 주문 서비스 — kis_order.py 하위 호환 re-export.

해외주식 관련 함수만 노출한다.
"""

from app.services.kis_order import (  # noqa: F401 — public API re-exports
    OrderResult,
    is_market_open,
    place_overseas_order,
)
