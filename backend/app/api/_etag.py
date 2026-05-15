"""ETag/304 응답 헬퍼 — payload 직렬화 + sha256 ETag + If-None-Match 매치.

캐싱 가능 read-only 엔드포인트에서 일관된 캐시 헤더를 부여한다.
DB 데이터(분석 등)는 hash 가 안정적이라 매우 효과적이다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request
from fastapi.responses import Response as FastAPIResponse


def etag_response(request: Request, payload: Any) -> FastAPIResponse:
    """payload 를 JSON 직렬화하고 sha256(첫 16자) ETag 를 발급한다.

    If-None-Match 가 일치하면 304 Not Modified (본문 없음).
    그 외에는 200 응답 + ETag 헤더.

    payload 는 dict / list / pydantic dump 결과 등 json-직렬화 가능한 값.
    Decimal/datetime 등은 default=str 로 자동 직렬화된다.
    """
    body = json.dumps(payload, default=str, sort_keys=True)
    etag = hashlib.sha256(body.encode()).hexdigest()[:16]
    if_none_match = request.headers.get("if-none-match", "")
    if if_none_match == etag:
        return FastAPIResponse(status_code=304, headers={"ETag": etag})
    return FastAPIResponse(
        content=body, media_type="application/json", headers={"ETag": etag}
    )
