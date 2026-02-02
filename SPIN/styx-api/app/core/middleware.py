from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request

from app.core.envelope import CacheInfo, Timing

REQUEST_ID_HEADER = "X-Request-Id"
_request_logger = logging.getLogger("styx.request")


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
    req_id = getattr(request.state, "request_id", None) or request.headers.get(REQUEST_ID_HEADER, "-")
    client_ip = request.client.host if request.client else None
    parts = [
        f"request_id={req_id}",
        f"method={request.method}",
        f"path={request.url.path}",
        f"status_code={response.status_code}",
        f"duration_ms={elapsed_ms:.2f}",
    ]
    if client_ip:
        parts.append(f"client_ip={client_ip}")
    _request_logger.info(" ".join(parts))
    return response
