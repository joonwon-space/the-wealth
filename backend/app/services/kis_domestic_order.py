"""국내주식 주문 서비스 — kis_order.py 하위 호환 re-export.

국내주식 관련 함수만 노출한다.
"""

from app.services.kis_order import (  # noqa: F401 — public API re-exports
    OrderableInfo,
    OrderResult,
    get_orderable_quantity,
    is_market_open,
    place_domestic_order,
)
