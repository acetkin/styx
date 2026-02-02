from __future__ import annotations

import json
import logging
from typing import Iterable

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.core.envelope import ErrorItem, envelope_response
from app.core.middleware import REQUEST_ID_HEADER


_error_logger = logging.getLogger("styx.error")


def _loc_to_path(loc: Iterable[object]) -> str:
    parts = list(loc)
    if parts and parts[0] == "body":
        parts = parts[1:]
    if not parts:
        return "/"
    return "/" + "/".join(str(part) for part in parts)


def _code_for_validation_error(error_type: str) -> str:
    if error_type == "extra_forbidden":
        return "UNKNOWN_FIELD"
    if error_type in {"literal_error", "enum"} or error_type.startswith("enum"):
        return "UNSUPPORTED_VALUE"
    return "VALIDATION_ERROR"


def _hint_for_validation_error(code: str) -> str | None:
    if code == "UNKNOWN_FIELD":
        return "Remove unknown field(s)."
    if code == "UNSUPPORTED_VALUE":
        return "Use an allowed value from /v1/config."
    return None


def _error_items_from_validation_error(exc: RequestValidationError) -> list[ErrorItem]:
    items: list[ErrorItem] = []
    for err in exc.errors():
        error_type = err.get("type", "")
        code = _code_for_validation_error(error_type)
        items.append(
            ErrorItem(
                code=code,
                message=err.get("msg", "Invalid request"),
                path=_loc_to_path(err.get("loc", [])),
                hint=_hint_for_validation_error(code),
            )
        )
    return items


def _stringify_detail(detail: object) -> str:
    if isinstance(detail, (dict, list)):
        return json.dumps(detail, ensure_ascii=True)
    return str(detail)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return envelope_response(
        request=request,
        data=None,
        errors=_error_items_from_validation_error(exc),
        status_code=422,
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        return envelope_response(
            request=request,
            data=None,
            errors=[
                ErrorItem(
                    code="INTERNAL_ERROR",
                    message="Internal server error",
                    path="/",
                )
            ],
            status_code=exc.status_code,
        )
    code = "VALIDATION_ERROR" if exc.status_code == 422 else f"HTTP_{exc.status_code}"
    return envelope_response(
        request=request,
        data=None,
        errors=[
            ErrorItem(
                code=code,
                message=_stringify_detail(exc.detail),
                path="/",
            )
        ],
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None) or request.headers.get(REQUEST_ID_HEADER, "-")
    _error_logger.exception(
        "internal_error request_id=%s method=%s path=%s",
        req_id,
        request.method,
        request.url.path,
    )
    return envelope_response(
        request=request,
        data=None,
        errors=[
            ErrorItem(
                code="INTERNAL_ERROR",
                message="Internal server error",
                path="/",
            )
        ],
        status_code=500,
    )
