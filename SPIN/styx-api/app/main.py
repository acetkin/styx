"""FastAPI entry point."""

from datetime import datetime, timezone, timedelta
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
    TRANSIT_ORB_TABLE,
)
from app.models import ChartRequest, LocationObj, Settings, TransitRequest, TimelineRequest, ProgressionTimelineRequest
from app.core.envelope import Settings as EnvelopeSettings
from app.core.envelope import ZodiacSettings, envelope_response
from app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.core.middleware import request_id_middleware, timing_middleware
from app.services.lunations import filter_lunations
from app.services.astro import (
    _build_aspect_targets,
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


@app.get("/v1/health")
def health(request: Request):
    settings = EnvelopeSettings(
        zodiac=ZodiacSettings(type=DEFAULT_ZODIAC),
        house_system=DEFAULT_HOUSE_SYSTEM,
    )
    return envelope_response(
        request=request,
        data={"status": "ok"},
        settings=settings,
        input_summary=None,
    )


@app.get("/v1/config")
def config() -> dict:
    return {
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


@app.post("/v1/chart")
def chart(req: ChartRequest, request: Request) -> dict:
    settings = req.settings or Settings()
    timestamp_utc = _resolve_timestamp(req.metadata.timestamp_utc)
    location = _resolve_location(req.metadata.location, request)

    try:
        payload = calc_chart(
            chart_type=req.metadata.chart_type,
            timestamp_utc=timestamp_utc,
            location=location,
            settings=settings,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    name = req.metadata.name or (req.subject.name if req.subject else None)
    base_meta = dict(payload["meta"])
    base_meta.pop("name", None)
    payload["meta"] = {"name": name, **base_meta}
    return payload


def _label_from_frame(frame: ChartRequest) -> str:
    label = frame.metadata.chart_type
    return str(label)


@app.post("/v1/transit")
def transit(req: TransitRequest, request: Request) -> dict:
    transit_type = req.metadata.transit_type

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
        return payload

    if transit_type not in {"transit", "on_natal", "synastry", "astrocartography", "solar_arc", "secondary_progression"}:
        raise HTTPException(status_code=422, detail=f"Unsupported transit_type: {transit_type}")

    if req.frame_a is None:
        raise HTTPException(status_code=422, detail="frame_a is required for this transit_type")

    frame_a_req = req.frame_a
    frame_b_req = req.frame_b

    def _resolve_frame(frame: ChartRequest) -> dict:
        settings = frame.settings or Settings()
        timestamp_utc = _resolve_timestamp(frame.metadata.timestamp_utc)
        location = _resolve_location(frame.metadata.location, request)
        return calc_chart(
            chart_type=frame.metadata.chart_type,
            timestamp_utc=timestamp_utc,
            location=location,
            settings=settings,
            round_output=False,
        )

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
        return round_payload(payload, 2)

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

        arc_bodies = {}
        for name, body in frame_a_chart["bodies"].items():
            arc_bodies[name] = {**body, "lon": _normalize_deg(body["lon"] + arc)}

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
                "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
                "solar_arc_sun": sun_mode,
            },
            "aspects": aspects,
        }
        return round_payload(payload, 2)

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

        if req.metadata.output == "chart":
            meta = progressed_chart.get("meta", {})
            meta["output_type"] = "secondary_progression"
            meta["mode"] = "chart"
            meta["chart_type"] = "secondary_progression"
            meta["transit_type"] = transit_type
            meta["target_timestamp_utc"] = frame_b_chart["meta"]["timestamp_utc"]
            progressed_chart["meta"] = meta
            return round_payload(progressed_chart, 2)

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
                "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
            },
            "aspects": aspects,
        }
        return round_payload(payload, 2)

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

    name_a = frame_a_req.metadata.name or (frame_a_req.subject.name if frame_a_req.subject else None)
    name_b = frame_b_req.metadata.name or (frame_b_req.subject.name if frame_b_req.subject else None)
    meta = {
        "transit_type": transit_type,
        "timestamp_utc": frame_b_chart["meta"]["timestamp_utc"],
    }

    payload = {
        "meta": meta,
        "aspects": aspects,
    }

    return round_payload(payload, 2)


@app.post("/v1/timeline")
def timeline(req: TimelineRequest, request: Request) -> dict:
    settings = req.settings or req.natal.settings or Settings()
    natal_location = _resolve_location(req.natal.metadata.location, request)
    natal_timestamp = _resolve_timestamp(req.natal.metadata.timestamp_utc)

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
        return {
            "meta": {
                "start_utc": req.metadata.start_utc,
                "end_utc": req.metadata.end_utc,
                "level": level,
            },
            "events": events,
        }

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

    return payload


@app.post("/v1/progression_timeline")
def progression_timeline(req: ProgressionTimelineRequest, request: Request) -> dict:
    settings = req.settings or req.natal.settings or Settings()
    natal_location = _resolve_location(req.natal.metadata.location, request)
    natal_timestamp = _resolve_timestamp(req.natal.metadata.timestamp_utc)

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
    return payload
