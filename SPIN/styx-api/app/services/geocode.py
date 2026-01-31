from __future__ import annotations

import json
import os
import ipaddress
from dataclasses import dataclass
import time
from typing import Optional
import urllib.request

from geopy.geocoders import Nominatim


@dataclass
class GeoResult:
    lat: float
    lon: float
    alt_m: float
    place: Optional[str]


def _parse_stub(value: str) -> Optional[GeoResult]:
    raw = value.strip()
    if not raw:
        return None

    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return GeoResult(lat=0.0, lon=0.0, alt_m=0.0, place="STUB")

    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
            return GeoResult(
                lat=float(payload["lat"]),
                lon=float(payload["lon"]),
                alt_m=float(payload.get("alt_m", 0.0)),
                place=payload.get("place"),
            )
        except Exception:
            return None

    parts = [p.strip() for p in raw.split(",")]
    if len(parts) >= 2:
        try:
            lat = float(parts[0])
            lon = float(parts[1])
            alt_m = float(parts[2]) if len(parts) >= 3 and parts[2] else 0.0
            place = parts[3] if len(parts) >= 4 and parts[3] else None
            return GeoResult(lat=lat, lon=lon, alt_m=alt_m, place=place)
        except Exception:
            return None

    return None


def geocode_place(place: str) -> GeoResult:
    stub = os.getenv("STYX_GEOCODE_STUB")
    if stub:
        parsed = _parse_stub(stub)
        if parsed:
            return parsed

    user_agent = os.getenv("STYX_GEOCODE_USER_AGENT", "styx-api")
    timeout = float(os.getenv("STYX_GEOCODE_TIMEOUT", "10"))
    domain = os.getenv("STYX_GEOCODE_DOMAIN")
    country_codes = os.getenv("STYX_GEOCODE_COUNTRY_CODES")
    language = os.getenv("STYX_GEOCODE_LANGUAGE")

    geolocator = Nominatim(user_agent=user_agent, domain=domain) if domain else Nominatim(user_agent=user_agent)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            location = geolocator.geocode(
                place,
                timeout=timeout,
                country_codes=country_codes,
                language=language,
            )
            if location:
                break
        except Exception as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(0.5 + attempt * 0.5)
    else:
        location = None

    if not location:
        detail = f": {last_error}" if last_error else ""
        raise ValueError(f"Geocoding failed for '{place}'{detail}")

    return GeoResult(
        lat=float(location.latitude),
        lon=float(location.longitude),
        alt_m=0.0,
        place=place,
    )


def _is_private_ip(value: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_reserved
        or ip_obj.is_link_local
    )


def _geoip_url(ip_value: str) -> str:
    template = os.getenv("STYX_GEOIP_URL", "https://ipapi.co/{ip}/json/")
    if "{ip}" in template:
        return template.format(ip=ip_value)
    if ip_value:
        return template.rstrip("/") + f"/{ip_value}"
    return template


def geocode_ip(ip_value: str) -> GeoResult:
    stub = os.getenv("STYX_GEOIP_STUB")
    if stub:
        parsed = _parse_stub(stub)
        if parsed:
            return parsed

    ip_value = (ip_value or "").strip()
    if ip_value and _is_private_ip(ip_value):
        ip_value = ""

    url = _geoip_url(ip_value)
    timeout = float(os.getenv("STYX_GEOIP_TIMEOUT", "5"))

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:
        raise ValueError(f"GeoIP failed for '{ip_value or 'auto'}': {exc}") from exc

    if isinstance(payload, dict) and payload.get("error"):
        reason = payload.get("reason") or payload.get("message") or "unknown"
        raise ValueError(f"GeoIP failed for '{ip_value or 'auto'}': {reason}")

    lat = payload.get("latitude") if isinstance(payload, dict) else None
    lon = payload.get("longitude") if isinstance(payload, dict) else None
    if lat is None and isinstance(payload, dict):
        lat = payload.get("lat")
    if lon is None and isinstance(payload, dict):
        lon = payload.get("lon")

    if lat is None or lon is None:
        raise ValueError(f"GeoIP failed for '{ip_value or 'auto'}': missing lat/lon")

    place_parts = []
    if isinstance(payload, dict):
        for key in ("city", "region", "country_name", "country"):
            value = payload.get(key)
            if value:
                place_parts.append(str(value))
        if not place_parts:
            for key in ("country_code", "continent_code"):
                value = payload.get(key)
                if value:
                    place_parts.append(str(value))

    place = ", ".join(place_parts) if place_parts else None
    return GeoResult(lat=float(lat), lon=float(lon), alt_m=0.0, place=place)
