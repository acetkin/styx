from __future__ import annotations

from datetime import datetime, timezone
import time
import uuid
from typing import Any, Generic, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.version import API_VERSION, ENGINE_VERSION, EPHEMERIS_PROVIDER, SCHEMA_VERSION

T = TypeVar("T")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EphemerisInfo(BaseModel):
    provider: str
    version: str | None = None
    flags: dict[str, Any] | list[str] | None = None


class Meta(BaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION)
    api_version: str = Field(default=API_VERSION)
    engine_version: str = Field(default=ENGINE_VERSION)
    request_id: str
    created_at_utc: str
    ephemeris: EphemerisInfo | None = None


class ZodiacSettings(BaseModel):
    type: str
    ayanamsa: str | None = None


class CoordinatesSettings(BaseModel):
    frame: str
    unit: str


class OrbsSettings(BaseModel):
    policy: str
    aspects: dict[str, float] | dict[str, Any] = Field(default_factory=dict)
    luminary_bonus: float | None = None


class Settings(BaseModel):
    zodiac: ZodiacSettings | None = None
    house_system: str | None = None
    coordinates: CoordinatesSettings | None = None
    orbs: OrbsSettings | None = None


class LocationSummary(BaseModel):
    lat: float | None = None
    lon: float | None = None


class InputSummary(BaseModel):
    datetime_local: str | None = None
    timezone: str | None = None
    datetime_utc: str | None = None
    location: LocationSummary | None = None


class CacheInfo(BaseModel):
    hit: bool
    key: str | None = None


class Timing(BaseModel):
    latency_ms: float
    compute_ms: float
    cache: CacheInfo | None = None


class ErrorItem(BaseModel):
    code: str
    message: str
    path: str
    hint: str | None = None


class Envelope(BaseModel, Generic[T]):
    meta: Meta
    settings: Settings | None = None
    input_summary: InputSummary | None = None
    data: T | None = None
    timing: Timing | None = None
    errors: list[ErrorItem] = Field(default_factory=list)


DEFAULT_ORB_ASPECTS: dict[str, float] = {
    "conjunction": 8,
    "opposition": 8,
    "trine": 7,
    "square": 7,
    "sextile": 5,
}
DEFAULT_ORB_POLICY = "default_v1"
DEFAULT_LUMINARY_BONUS = 2.0
DEFAULT_COORD_FRAME = "ecliptic"
DEFAULT_COORD_UNIT = "deg"
DEFAULT_ZODIAC_TYPE = "tropical"
DEFAULT_HOUSE_SYSTEM = "placidus"


def default_settings() -> Settings:
    return Settings(
        zodiac=ZodiacSettings(type=DEFAULT_ZODIAC_TYPE),
        house_system=DEFAULT_HOUSE_SYSTEM,
        coordinates=CoordinatesSettings(frame=DEFAULT_COORD_FRAME, unit=DEFAULT_COORD_UNIT),
        orbs=OrbsSettings(
            policy=DEFAULT_ORB_POLICY,
            aspects=DEFAULT_ORB_ASPECTS,
            luminary_bonus=DEFAULT_LUMINARY_BONUS,
        ),
    )


def default_input_summary() -> InputSummary:
    return InputSummary(
        datetime_local=None,
        timezone=None,
        datetime_utc=None,
        location=LocationSummary(lat=None, lon=None),
    )


def build_envelope(
    *,
    data: Any = None,
    settings: Settings | None = None,
    input_summary: InputSummary | None = None,
    request_id: str,
    timing: Timing | None,
    errors: list[ErrorItem] | None = None,
    ephemeris: EphemerisInfo | None = None,
) -> Envelope[Any]:
    meta = Meta(
        request_id=request_id,
        created_at_utc=_utc_now_iso(),
        ephemeris=ephemeris or EphemerisInfo(provider=EPHEMERIS_PROVIDER),
    )
    return Envelope(
        meta=meta,
        settings=settings,
        input_summary=input_summary,
        data=data,
        timing=timing,
        errors=errors or [],
    )


def _resolve_request_id(request: Request) -> str:
    req_id = getattr(request.state, "request_id", None)
    if req_id:
        return req_id
    header_id = request.headers.get("X-Request-Id")
    if header_id:
        return header_id
    return str(uuid.uuid4())


def _resolve_timing(request: Request) -> Timing:
    timing = getattr(request.state, "timing", None)
    if timing:
        return timing
    start = getattr(request.state, "start_time", None)
    if start is None:
        return Timing(latency_ms=0.0, compute_ms=0.0, cache=CacheInfo(hit=False))
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return Timing(latency_ms=elapsed_ms, compute_ms=elapsed_ms, cache=CacheInfo(hit=False))


_MISSING = object()


def envelope_response(
    *,
    request: Request,
    data: Any = None,
    settings: Settings | None = None,
    input_summary: InputSummary | None | object = _MISSING,
    errors: list[ErrorItem] | None = None,
    timing: Timing | None = None,
    status_code: int = 200,
) -> JSONResponse:
    req_id = _resolve_request_id(request)
    timing_obj = timing or _resolve_timing(request)
    settings_obj = settings or default_settings()
    if input_summary is _MISSING:
        input_summary_obj = default_input_summary()
    else:
        input_summary_obj = input_summary
    envelope = build_envelope(
        data=data,
        settings=settings_obj,
        input_summary=input_summary_obj,
        request_id=req_id,
        timing=timing_obj,
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(exclude_none=False),
        headers={"X-Request-Id": req_id},
    )
