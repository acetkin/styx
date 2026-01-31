from __future__ import annotations

import json
from typing import Iterable

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.core.envelope import ErrorItem, envelope_response


def _format_loc(loc: Iterable[object]) -> str | None:
    parts = [str(item) for item in loc if item not in {"body", "query", "path", "header"}]
    if not parts:
        parts = [str(item) for item in loc]
    return ".".join(parts) if parts else None


def _error_items_from_validation_error(exc: RequestValidationError) -> list[ErrorItem]:
    items: list[ErrorItem] = []
    for err in exc.errors():
        field = _format_loc(err.get("loc", []))
        items.append(
            ErrorItem(
                code="VALIDATION_ERROR",
                message=err.get("msg", "Invalid request"),
                field=field,
                hint=err.get("type"),
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
    return envelope_response(
        request=request,
        data=None,
        errors=[ErrorItem(code=f"HTTP_{exc.status_code}", message=_stringify_detail(exc.detail))],
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    return envelope_response(
        request=request,
        data=None,
        errors=[ErrorItem(code="INTERNAL_ERROR", message="Internal server error")],
        status_code=500,
    )

