from __future__ import annotations

import time
import uuid

from fastapi import Request

from app.core.envelope import CacheInfo, Timing

REQUEST_ID_HEADER = "X-Request-Id"


async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get(REQUEST_ID_HEADER)
    if not req_id:
        req_id = str(uuid.uuid4())
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers.setdefault(REQUEST_ID_HEADER, req_id)
    return response


async def timing_middleware(request: Request, call_next):
    request.state.start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - request.state.start_time) * 1000.0
    request.state.timing = Timing(
        latency_ms=elapsed_ms,
        compute_ms=elapsed_ms,
        cache=CacheInfo(hit=False),
    )
    return response

