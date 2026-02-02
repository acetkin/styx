"""FastAPI entry point."""

from datetime import datetime, timezone, timedelta
from copy import deepcopy
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.config import (
    ASTEROID_ORDER,
    ASPECT_ORBS,
    ASPECT_SET,
    DEFAULT_COORDINATE_SYSTEM,
    DEFAULT_HOUSE_SYSTEM,
    DEFAULT_STAR_ORB,
    DEFAULT_ZODIAC,
    PLANET_ORDER,
    DEFAULT_FIXED_STARS,
    SIGNS,
    TRANSIT_ORB_TABLE,
)
from app.models import ChartRequest, LocationObj, Settings, TransitRequest, TimelineRequest, ProgressionTimelineRequest
from app.core.envelope import (
    CoordinatesSettings,
    InputSummary,
    LocationSummary,
    OrbsSettings,
    Settings as EnvelopeSettings,
    ZodiacSettings,
    envelope_response,
)
from app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.core.middleware import request_id_middleware, timing_middleware
from app.services.lunations import filter_lunations
from app.services.astro import (
    _build_aspect_targets,
    _calc_aspects,
    _calc_cross_aspects,
    _default_aspect_config,
    _normalize_deg,
    _parse_timestamp,
    calc_astrocartography,
    calc_chart,
    get_provenance,
    round_payload,
)
from app.services.geocode import geocode_ip, geocode_place
from app.services.timeline import build_timeline
from app.services.progression_timeline import build_progression_timeline

app = FastAPI(title="STYX API", version="0.1.0")
app.middleware("http")(request_id_middleware)
app.middleware("http")(timing_middleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

DEFAULT_ORB_ASPECTS = {
    "conjunction": 8,
    "opposition": 8,
    "trine": 7,
    "square": 7,
    "sextile": 5,
}
DEFAULT_ORB_POLICY = "default_v1"
DEFAULT_LUMINARY_BONUS = 2.0


def _sign_and_degree(lon: float) -> tuple[str, float]:
    normalized = _normalize_deg(lon)
    return SIGNS[int(normalized // 30)], normalized % 30.0


def _shift_angle_payload(payload: dict, arc: float) -> dict:
    shifted = dict(payload)
    lon = _normalize_deg(float(payload["lon"]) + arc)
    sign, deg_in_sign = _sign_and_degree(lon)
    shifted["lon"] = lon
    shifted["sign"] = sign
    shifted["deg_in_sign"] = deg_in_sign
    return shifted


def _shift_body_payload(payload: dict, arc: float) -> dict:
    shifted = dict(payload)
    lon = _normalize_deg(float(payload["lon"]) + arc)
    sign, deg_in_sign = _sign_and_degree(lon)
    shifted["lon"] = lon
    shifted["sign"] = sign
    shifted["deg_in_sign"] = deg_in_sign
    return shifted


def _build_solar_arc_chart_payload(frame_a_chart: dict, frame_b_chart: dict, arc: float, sun_mode: str) -> dict:
    chart = deepcopy(frame_a_chart)

    chart["bodies"] = {name: _shift_body_payload(body, arc) for name, body in frame_a_chart["bodies"].items()}
    chart["asteroids"] = {name: _shift_body_payload(body, arc) for name, body in frame_a_chart.get("asteroids", {}).items()}
    chart["angles"] = {name: _shift_angle_payload(payload, arc) for name, payload in frame_a_chart["angles"].items()}

    houses = deepcopy(frame_a_chart["houses"])
    cusps = houses.get("cusps", {})
    houses["cusps"] = {name: _shift_angle_payload(payload, arc) for name, payload in cusps.items()}
    chart["houses"] = houses

    points = deepcopy(frame_a_chart.get("points", {}))
    for key in ("nn", "sn", "lilith (black moon)"):
        if key in points:
            points[key] = _shift_body_payload(points[key], arc)
    if isinstance(points.get("lots"), dict):
        points["lots"] = {name: _shift_body_payload(payload, arc) for name, payload in points["lots"].items()}
    chart["points"] = points

    _, aspect_angles, aspect_orbs, aspect_classes = _default_aspect_config()
    chart["aspects"] = _calc_aspects(
        _build_aspect_targets(chart),
        aspect_angles,
        aspect_orbs,
        aspect_classes,
    )
    chart["stars"] = []

    meta = dict(chart.get("meta", {}))
    meta["output_type"] = "solar_arc"
    meta["mode"] = "chart"
    meta["chart_type"] = "solar_arc"
    meta["solar_arc_sun"] = sun_mode
    meta["solar_arc_deg"] = arc
    meta["source_timestamp_utc"] = frame_a_chart["meta"]["timestamp_utc"]
    meta["target_timestamp_utc"] = frame_b_chart["meta"]["timestamp_utc"]
    meta["timestamp_utc"] = frame_b_chart["meta"]["timestamp_utc"]
    chart["meta"] = meta
    return chart


def _build_envelope_settings(settings: Settings | None) -> EnvelopeSettings:
    resolved = settings or Settings()
    return EnvelopeSettings(
        zodiac=ZodiacSettings(type=resolved.zodiac or DEFAULT_ZODIAC),
        house_system=resolved.house_system or DEFAULT_HOUSE_SYSTEM,
        coordinates=CoordinatesSettings(
            frame=resolved.coordinate_system or DEFAULT_COORDINATE_SYSTEM,
            unit="deg",
        ),
        orbs=OrbsSettings(
            policy=DEFAULT_ORB_POLICY,
            aspects=DEFAULT_ORB_ASPECTS,
            luminary_bonus=DEFAULT_LUMINARY_BONUS,
        ),
    )


def _build_input_summary(timestamp_utc: str | None, location: dict | None) -> InputSummary:
    loc = LocationSummary(
        lat=location.get("lat") if location else None,
        lon=location.get("lon") if location else None,
    )
    tz = "UTC" if timestamp_utc else None
    return InputSummary(
        datetime_local=timestamp_utc,
        timezone=tz,
        datetime_utc=timestamp_utc,
        location=loc,
    )


@app.get("/v1/health")
def health(request: Request):
    settings = _build_envelope_settings(None)
    return envelope_response(
        request=request,
        data={"status": "ok"},
        settings=settings,
        input_summary=None,
    )


@app.get("/v1/config")
def config(request: Request):
    payload = {
        "defaults": {
            "house_system": DEFAULT_HOUSE_SYSTEM,
            "zodiac": DEFAULT_ZODIAC,
            "coordinate_system": DEFAULT_COORDINATE_SYSTEM,
            "star_orb": DEFAULT_STAR_ORB,
            "points": {"lilith": "mean"},
        },
        "catalogs": {
            "planets": PLANET_ORDER,
            "asteroids": ASTEROID_ORDER,
            "fixed_stars": DEFAULT_FIXED_STARS,
        },
        "aspects": {
            "set": ASPECT_SET,
            "orbs": {str(int(k)): v for k, v in ASPECT_ORBS.items()},
        },
        "transit_orbs": TRANSIT_ORB_TABLE,
        "provenance": get_provenance(),
    }
    return envelope_response(
        request=request,
        data=payload,
        settings=_build_envelope_settings(None),
        input_summary=None,
    )


def _resolve_timestamp(raw: str | None) -> str:
    if raw:
        if raw.strip().lower() == "now":
            return datetime.now(timezone.utc).isoformat()
        return raw
    return datetime.now(timezone.utc).isoformat()


def _parse_auto_location(raw: str) -> tuple[bool, str | None]:
    stripped = raw.strip()
    lowered = stripped.lower()
    if lowered in {"auto", "ip"}:
        return True, None
    if lowered.startswith("auto"):
        for delimiter in (":", "|", ","):
            if delimiter in stripped:
                _, fallback = stripped.split(delimiter, 1)
                fallback = fallback.strip()
                return True, fallback or None
        return True, None
    return False, None


def _resolve_location(location_input, request: Request) -> dict:
    fallback_place: str | None = None
    use_auto = False

    if location_input is None:
        use_auto = True
    elif isinstance(location_input, str):
        raw = location_input.strip()
        if not raw:
            use_auto = True
        else:
            use_auto, fallback_place = _parse_auto_location(raw)
            if not use_auto:
                try:
                    geo = geocode_place(raw)
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
                return {
                    "lat": geo.lat,
                    "lon": geo.lon,
                    "alt_m": geo.alt_m,
                    "place": geo.place or raw,
                }
    else:
        assert isinstance(location_input, LocationObj)
        return {
            "lat": location_input.lat,
            "lon": location_input.lon,
            "alt_m": location_input.alt_m,
            "place": location_input.place,
        }

    if use_auto:
        client_ip = request.client.host if request.client else ""
        try:
            geo = geocode_ip(client_ip)
        except ValueError as exc:
            if fallback_place:
                try:
                    geo = geocode_place(fallback_place)
                except ValueError as fallback_exc:
                    raise HTTPException(status_code=422, detail=str(fallback_exc)) from fallback_exc
            else:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "lat": geo.lat,
            "lon": geo.lon,
            "alt_m": geo.alt_m,
            "place": geo.place or fallback_place or "auto",
        }

    raise HTTPException(status_code=422, detail="Location is required")


def _resolve_chart_frame(frame: ChartRequest, request: Request, *, allow_derived: bool = False) -> tuple[dict, str, dict, Settings]:
    if not allow_derived and frame.metadata.chart_type not in {"natal", "moment"}:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported frame chart_type for this endpoint: {frame.metadata.chart_type}",
        )
    settings = frame.settings or Settings()
    timestamp_utc = _resolve_timestamp(frame.metadata.timestamp_utc)
    location = _resolve_location(frame.metadata.location, request)
    try:
        payload = calc_chart(
            chart_type=frame.metadata.chart_type,
            timestamp_utc=timestamp_utc,
            location=location,
            settings=settings,
            round_output=False,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return payload, timestamp_utc, location, settings


@app.post("/v1/chart")
def chart(req: ChartRequest, request: Request) -> dict:
    chart_type = req.metadata.chart_type
    name = None

    if chart_type in {"natal", "moment"}:
        settings = req.settings or Settings()
        timestamp_utc = _resolve_timestamp(req.metadata.timestamp_utc)
        location = _resolve_location(req.metadata.location, request)
        try:
            payload = calc_chart(
                chart_type=chart_type,
                timestamp_utc=timestamp_utc,
                location=location,
                settings=settings,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        base_meta = dict(payload["meta"])
        base_meta.pop("name", None)
        payload["meta"] = {"name": name, **base_meta}
        return envelope_response(
            request=request,
            data=payload,
            settings=_build_envelope_settings(settings),
            input_summary=_build_input_summary(timestamp_utc, location),
        )

    if chart_type == "solar_arc":
        if req.frame_a is None:
            raise HTTPException(status_code=422, detail="frame_a is required for chart_type=solar_arc")
        if req.frame_a.metadata.chart_type != "natal":
            raise HTTPException(status_code=422, detail="frame_a.chart_type must be natal for chart_type=solar_arc")

        frame_a_chart, _, _, frame_a_settings = _resolve_chart_frame(req.frame_a, request)
        target_settings = req.settings or frame_a_settings
        target_timestamp_utc = _resolve_timestamp(req.metadata.timestamp_utc)
        target_location = _resolve_location(req.metadata.location or req.frame_a.metadata.location, request)

        try:
            frame_b_chart = calc_chart(
                chart_type="moment",
                timestamp_utc=target_timestamp_utc,
                location=target_location,
                settings=target_settings,
                round_output=False,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        sun_mode = req.metadata.solar_arc_sun or "mean"
        sun_key = "sun"
        if sun_mode == "true":
            sun_key = "sun_true"
            if "sun_true" not in frame_a_chart["bodies"]:
                frame_a_chart["bodies"]["sun_true"] = frame_a_chart["bodies"]["sun"]
            if "sun_true" not in frame_b_chart["bodies"]:
                frame_b_chart["bodies"]["sun_true"] = frame_b_chart["bodies"]["sun"]
        arc = _normalize_deg(frame_b_chart["bodies"][sun_key]["lon"] - frame_a_chart["bodies"][sun_key]["lon"])

        payload = _build_solar_arc_chart_payload(frame_a_chart, frame_b_chart, arc, sun_mode)
        payload = round_payload(payload, 2)
        base_meta = dict(payload["meta"])
        base_meta.pop("name", None)
        payload["meta"] = {"name": name, **base_meta}
        return envelope_response(
            request=request,
            data=payload,
            settings=_build_envelope_settings(target_settings),
            input_summary=_build_input_summary(target_timestamp_utc, target_location),
        )

    if chart_type == "secondary_progression":
        if req.frame_a is None:
            raise HTTPException(status_code=422, detail="frame_a is required for chart_type=secondary_progression")
        if req.frame_a.metadata.chart_type != "natal":
            raise HTTPException(
                status_code=422,
                detail="frame_a.chart_type must be natal for chart_type=secondary_progression",
            )

        frame_a_chart, frame_a_timestamp_utc, frame_a_location, frame_a_settings = _resolve_chart_frame(req.frame_a, request)
        target_settings = req.settings or frame_a_settings
        target_timestamp_utc = _resolve_timestamp(req.metadata.timestamp_utc)
        target_location = _resolve_location(req.metadata.location or req.frame_a.metadata.location, request)

        natal_dt = _parse_timestamp(frame_a_timestamp_utc)
        target_dt = _parse_timestamp(target_timestamp_utc)
        delta_years = (target_dt - natal_dt).total_seconds() / (365.25 * 86400.0)
        progressed_dt = natal_dt + timedelta(days=delta_years)
        progressed_ts = progressed_dt.isoformat()

        try:
            payload = calc_chart(
                chart_type="natal",
                timestamp_utc=progressed_ts,
                location=frame_a_chart["meta"]["location"],
                settings=target_settings,
                round_output=False,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        meta = dict(payload.get("meta", {}))
        meta["output_type"] = "secondary_progression"
        meta["mode"] = "chart"
        meta["chart_type"] = "secondary_progression"
        meta["source_timestamp_utc"] = frame_a_timestamp_utc
        meta["target_timestamp_utc"] = target_timestamp_utc
        payload["meta"] = meta
        payload = round_payload(payload, 2)
        base_meta = dict(payload["meta"])
        base_meta.pop("name", None)
        payload["meta"] = {"name": name, **base_meta}
        return envelope_response(
            request=request,
            data=payload,
            settings=_build_envelope_settings(target_settings),
            input_summary=_build_input_summary(target_timestamp_utc, target_location or frame_a_location),
        )

    raise HTTPException(status_code=422, detail=f"Unsupported chart_type: {chart_type}")


def _label_from_frame(frame: ChartRequest) -> str:
    label = frame.metadata.chart_type
    return str(label)


@app.post("/v1/transit")
def transit(req: TransitRequest, request: Request) -> dict:
    transit_type = req.metadata.transit_type

    def _wrap(payload: dict, timestamp_utc: str | None, location: dict | None, settings: Settings | None):
        return envelope_response(
            request=request,
            data=payload,
            settings=_build_envelope_settings(settings),
            input_summary=_build_input_summary(timestamp_utc, location),
        )

    if transit_type == "lunations":
        if not req.metadata.start_utc or not req.metadata.end_utc:
            raise HTTPException(status_code=422, detail="start_utc and end_utc are required for lunations")
        events = filter_lunations(
            start_utc=req.metadata.start_utc,
            end_utc=req.metadata.end_utc,
            lunation_type=req.metadata.lunation_type,
            eclipse_kind=req.metadata.eclipse_kind,
        )
        payload = {
            "meta": {
                "transit_type": "lunations",
                "start_utc": req.metadata.start_utc,
                "end_utc": req.metadata.end_utc,
                "lunation_type": req.metadata.lunation_type or "all",
                "eclipse_kind": req.metadata.eclipse_kind or "",
            },
            "events": events,
        }
        return _wrap(payload, req.metadata.start_utc, None, None)

    if transit_type not in {"transit", "on_natal", "synastry", "astrocartography", "solar_arc", "secondary_progression"}:
        raise HTTPException(status_code=422, detail=f"Unsupported transit_type: {transit_type}")

    if req.frame_a is None:
        raise HTTPException(status_code=422, detail="frame_a is required for this transit_type")

    frame_a_req = req.frame_a
    frame_b_req = req.frame_b

    def _resolve_frame(frame: ChartRequest) -> dict:
        payload, _, _, _ = _resolve_chart_frame(frame, request)
        return payload

    if transit_type == "astrocartography":
        try:
            frame_a_chart = _resolve_frame(frame_a_req)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        settings = frame_a_req.settings or Settings()
        try:
            astro_payload = calc_astrocartography(frame_a_chart, settings.house_system, top_n=50)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        payload = {
            "meta": {
                "transit_type": transit_type,
                "timestamp_utc": frame_a_chart["meta"]["timestamp_utc"],
            },
            "results": astro_payload["results"],
            "crossings": astro_payload["crossings"],
        }
        payload = round_payload(payload, 2)
        return _wrap(payload, frame_a_chart["meta"]["timestamp_utc"], frame_a_chart["meta"]["location"], settings)

    if frame_b_req is None:
        if transit_type == "synastry":
            raise HTTPException(status_code=422, detail="frame_b is required for synastry")
        if transit_type == "solar_arc":
            frame_b_req = ChartRequest(
                metadata={
                    "chart_type": "natal",
                    "timestamp_utc": req.metadata.timestamp_utc,
                    "location": frame_a_req.metadata.location,
                },
                settings=Settings(),
            )
        else:
            frame_b_req = ChartRequest(
                metadata={
                    "chart_type": "moment",
                    "timestamp_utc": req.metadata.timestamp_utc,
                    "location": req.metadata.location or frame_a_req.metadata.location,
                },
                settings=Settings(),
            )

    if transit_type == "solar_arc":
        try:
            frame_a_chart = _resolve_frame(frame_a_req)
            frame_b_chart = _resolve_frame(frame_b_req)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        sun_mode = req.metadata.solar_arc_sun or "mean"
        sun_key = "sun"
        if sun_mode == "true":
            sun_key = "sun_true"
            if "sun_true" not in frame_a_chart["bodies"]:
                frame_a_chart["bodies"]["sun_true"] = frame_a_chart["bodies"]["sun"]
            if "sun_true" not in frame_b_chart["bodies"]:
                frame_b_chart["bodies"]["sun_true"] = frame_b_chart["bodies"]["sun"]

        arc = _normalize_deg(frame_b_chart["bodies"][sun_key]["lon"] - frame_a_chart["bodies"][sun_key]["lon"])

        arc_bodies = {name: {**body, "lon": _normalize_deg(body["lon"] + arc)} for name, body in frame_a_chart["bodies"].items()}

        aspect_set, aspect_angles, aspect_orbs, aspect_classes = _default_aspect_config()
        targets_a = [(name, arc_bodies[name]) for name in arc_bodies.keys()]
        targets_b = _build_aspect_targets(frame_a_chart)
        aspects = _calc_cross_aspects(
            targets_a,
            targets_b,
            aspect_angles,
            aspect_orbs,
            aspect_classes,
            "sa_",
            "natal_",
        )

        payload = {
            "meta": {
                "transit_type": transit_type,
                "mode": "aspects",
                "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
                "solar_arc_sun": sun_mode,
            },
            "aspects": aspects,
        }
        payload = round_payload(payload, 2)
        return _wrap(payload, frame_b_chart["meta"]["timestamp_utc"], frame_b_chart["meta"]["location"], frame_b_req.settings)

    if transit_type == "secondary_progression":
        try:
            frame_a_chart = _resolve_frame(frame_a_req)
            frame_b_chart = _resolve_frame(frame_b_req)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        natal_dt = _parse_timestamp(frame_a_req.metadata.timestamp_utc)
        target_dt = _parse_timestamp(frame_b_req.metadata.timestamp_utc)
        delta_years = (target_dt - natal_dt).total_seconds() / (365.25 * 86400.0)
        progressed_dt = natal_dt + timedelta(days=delta_years)
        progressed_ts = progressed_dt.isoformat()

        try:
            progressed_chart = calc_chart(
                chart_type="natal",
                timestamp_utc=progressed_ts,
                location=frame_a_chart["meta"]["location"],
                settings=frame_a_req.settings or Settings(),
                round_output=False,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        aspect_set, aspect_angles, aspect_orbs, aspect_classes = _default_aspect_config()
        targets_a = _build_aspect_targets(progressed_chart)
        targets_b = _build_aspect_targets(frame_a_chart)
        aspects = _calc_cross_aspects(
            targets_a,
            targets_b,
            aspect_angles,
            aspect_orbs,
            aspect_classes,
            "sp_",
            "natal_",
        )

        payload = {
            "meta": {
                "transit_type": transit_type,
                "mode": "aspects",
                "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
            },
            "aspects": aspects,
        }
        payload = round_payload(payload, 2)
        return _wrap(payload, frame_b_chart["meta"]["timestamp_utc"], frame_b_chart["meta"]["location"], frame_b_req.settings)

    try:
        frame_a_chart = _resolve_frame(frame_a_req)
        frame_b_chart = _resolve_frame(frame_b_req)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    label_a = _label_from_frame(frame_a_req)
    label_b = _label_from_frame(frame_b_req)
    if label_a == label_b:
        label_a = f"{label_a}_a"
        label_b = f"{label_b}_b"

    if transit_type in {"transit", "on_natal"}:
        prefix_a = "natal_"
        prefix_b = "tr_"
    else:
        prefix_a = f"{label_a}_"
        prefix_b = f"{label_b}_"

    aspect_set, aspect_angles, aspect_orbs, aspect_classes = _default_aspect_config()
    targets_a = _build_aspect_targets(frame_a_chart)
    targets_b = _build_aspect_targets(frame_b_chart)
    aspects = _calc_cross_aspects(
        targets_a,
        targets_b,
        aspect_angles,
        aspect_orbs,
        aspect_classes,
        prefix_a,
        prefix_b,
    )

    meta = {
        "transit_type": transit_type,
        "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
    }

    payload = {
        "meta": meta,
        "aspects": aspects,
    }

    payload = round_payload(payload, 2)
    return _wrap(payload, frame_b_chart["meta"]["timestamp_utc"], frame_b_chart["meta"]["location"], frame_b_req.settings)


@app.post("/v1/timeline")
def timeline(req: TimelineRequest, request: Request) -> dict:
    settings = req.settings or req.natal.settings or Settings()
    natal_location = _resolve_location(req.natal.metadata.location, request)
    natal_timestamp = _resolve_timestamp(req.natal.metadata.timestamp_utc)
    input_summary = _build_input_summary(natal_timestamp, natal_location)

    level = req.metadata.level
    body = (req.metadata.body or "").strip().lower() or None

    if level in {"level3", "lunations", "eclipses", "new_moon", "full_moon", "solar_eclipse", "lunar_eclipse"}:
        lunation_type = None
        if level == "eclipses":
            lunation_type = "solar_eclipse | lunar_eclipse"
        elif level in {"new_moon", "full_moon", "solar_eclipse", "lunar_eclipse"}:
            lunation_type = level
        events = filter_lunations(
            start_utc=req.metadata.start_utc,
            end_utc=req.metadata.end_utc,
            lunation_type=lunation_type,
        )
        return envelope_response(
            request=request,
            data={
                "meta": {
                    "start_utc": req.metadata.start_utc,
                    "end_utc": req.metadata.end_utc,
                    "level": level,
                },
                "events": events,
            },
            settings=_build_envelope_settings(settings),
            input_summary=input_summary,
        )

    try:
        natal_chart = calc_chart(
            chart_type="natal",
            timestamp_utc=natal_timestamp,
            location=natal_location,
            settings=settings,
            round_output=False,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    bodies = None
    if body:
        if body in {"nodes", "nn", "sn"}:
            bodies = ["nn", "sn"] if body == "nodes" else [body]
        elif body in {"jupiter", "saturn", "uranus", "neptune", "pluto"}:
            bodies = [body]
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported timeline body: {body}")

    try:
        payload = build_timeline(
            natal_chart=natal_chart,
            start_utc=req.metadata.start_utc,
            end_utc=req.metadata.end_utc,
            level=req.metadata.level,
            house_system=settings.house_system,
            bodies=bodies,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return envelope_response(
        request=request,
        data=payload,
        settings=_build_envelope_settings(settings),
        input_summary=input_summary,
    )


@app.post("/v1/progression_timeline")
def progression_timeline(req: ProgressionTimelineRequest, request: Request) -> dict:
    settings = req.settings or req.natal.settings or Settings()
    natal_location = _resolve_location(req.natal.metadata.location, request)
    natal_timestamp = _resolve_timestamp(req.natal.metadata.timestamp_utc)
    input_summary = _build_input_summary(natal_timestamp, natal_location)

    try:
        natal_chart = calc_chart(
            chart_type="natal",
            timestamp_utc=natal_timestamp,
            location=natal_location,
            settings=settings,
            round_output=False,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = build_progression_timeline(
        natal_chart=natal_chart,
        start_utc=req.metadata.start_utc,
        end_utc=req.metadata.end_utc,
        step_years=req.metadata.step_years or 1,
    )
    return envelope_response(
        request=request,
        data=payload,
        settings=_build_envelope_settings(settings),
        input_summary=input_summary,
    )
