from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import swisseph as swe

from app.config import TRANSIT_ORB_TABLE, SIGNS
from app.services.astro import (
    _aspect_delta,
    _calc_body,
    _calc_houses,
    _calc_obliquity,
    _ensure_ephe_path,
    _normalize_deg,
    _parse_timestamp,
    _assign_house,
)
from app.services.timeline import _natal_targets, _target_house_info


ASPECT_DEG = {
    0.0: "0",
    60.0: "60",
    90.0: "90",
    120.0: "120",
    180.0: "180",
}
ASPECT_ANGLES = list(ASPECT_DEG.keys())

STEP_SCHEDULE_DAYS = [30.0, 7.0, 1.0, 1.0 / 24.0, 1.0 / 1440.0]


def _scan_brackets_ts(func, start_ts: float, end_ts: float, step_seconds: float) -> list[tuple[float, float]]:
    brackets: list[tuple[float, float]] = []
    t = start_ts
    prev = func(t)
    while t < end_ts:
        t_next = min(t + step_seconds, end_ts)
        cur = func(t_next)
        if prev == 0:
            brackets.append((t, t))
        elif prev * cur <= 0:
            brackets.append((t, t_next))
        prev = cur
        t = t_next
    return brackets


def _adaptive_roots_ts(func, start_ts: float, end_ts: float) -> list[float]:
    brackets = [(start_ts, end_ts)]
    for days in STEP_SCHEDULE_DAYS:
        step_seconds = days * 86400.0
        refined: list[tuple[float, float]] = []
        for a, b in brackets:
            refined.extend(_scan_brackets_ts(func, a, b, step_seconds))
        brackets = refined
        if not brackets:
            return []
    roots: list[float] = []
    for a, b in brackets:
        root = _find_root(func, a, b)
        roots.append(root)
    dedup = sorted({round(r, 6) for r in roots})
    return dedup


def _adaptive_crossing_ts(func, start_ts: float, end_ts: float, forward: bool) -> float | None:
    if start_ts == end_ts:
        return start_ts
    brackets = [(start_ts, end_ts)]
    for days in STEP_SCHEDULE_DAYS:
        step_seconds = days * 86400.0
        refined: list[tuple[float, float]] = []
        for a, b in brackets:
            refined.extend(_scan_brackets_ts(func, a, b, step_seconds))
        if refined:
            brackets = refined
        if not brackets:
            return None
    chosen = brackets[0] if forward else brackets[-1]
    return _find_root(func, chosen[0], chosen[1])


@dataclass(frozen=True)
class Station:
    jd: float
    kind: str


def _to_jd(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000,
    )


def _from_ts_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _find_root(func, a: float, b: float, steps: int = 40) -> float:
    fa = func(a)
    fb = func(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    for _ in range(steps):
        mid = (a + b) / 2.0
        fm = func(mid)
        if fa * fm <= 0:
            b, fb = mid, fm
        else:
            a, fa = mid, fm
    return (a + b) / 2.0


def _sun_lon(dt_utc: datetime) -> float:
    jd = _to_jd(dt_utc)
    body = _calc_body(jd, swe.SUN, "sun")
    return float(body["lon"])


def _arc_at(dt_utc: datetime, natal_sun_lon: float) -> float:
    return _normalize_deg(_sun_lon(dt_utc) - natal_sun_lon)


def _solar_arc_body(natal_chart: dict, body: str, arc: float) -> tuple[float, float]:
    if body in {"nn", "sn"}:
        src = natal_chart["points"][body]
    else:
        src = natal_chart["bodies"][body]
    lon = _normalize_deg(float(src["lon"]) + arc)
    lat = float(src.get("lat", 0.0))
    return lon, lat


def _solar_arc_house_info(jd: float, lon: float, lat: float, location: dict, house_system: str) -> dict:
    cusps, _, _, armc, hsys = _calc_houses(jd, location["lat"], location["lon"], house_system)
    eps = _calc_obliquity(jd)
    house = _assign_house(lon, lat, cusps, armc, location["lat"], hsys, eps)
    cusp_lon = float(cusps[str(house)])
    sign = SIGNS[int(_normalize_deg(cusp_lon) // 30)]
    return {"house": house, "sign": sign}


def build_solar_arc_timeline(
    natal_chart: dict,
    start_utc: str,
    end_utc: str,
    bodies: List[str],
) -> dict:
    _ensure_ephe_path()

    start_dt = _parse_timestamp(start_utc)
    end_dt = _parse_timestamp(end_utc)

    location = natal_chart["meta"]["location"]
    house_system = natal_chart["houses"]["system"]
    natal_sun_lon = float(natal_chart["bodies"]["sun"]["lon"])

    targets = _natal_targets(natal_chart)

    events: List[dict] = []

    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

    for body in bodies:
        orb = TRANSIT_ORB_TABLE.get(body, TRANSIT_ORB_TABLE.get("nodes", 2.0))

        for target_name, target in targets:
            target_lon = target["lon"]
            natal_house = _target_house_info(natal_chart, target_name)

            for angle in ASPECT_ANGLES:
                aspect_deg = ASPECT_DEG[angle]
                exact_index = 0
                phases: List[dict] = []
                transit_start = None
                transit_end = None

                def delta_at(ts: float) -> float:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    arc = _arc_at(dt, natal_sun_lon)
                    lon, _ = _solar_arc_body(natal_chart, body, arc)
                    return _aspect_delta(lon, target_lon, angle)

                def orb_func(ts: float) -> float:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    arc = _arc_at(dt, natal_sun_lon)
                    lon, _ = _solar_arc_body(natal_chart, body, arc)
                    return abs(_aspect_delta(lon, target_lon, angle)) - orb

                exact_ts_list = _adaptive_roots_ts(delta_at, start_ts, end_ts)
                for exact_ts in exact_ts_list:
                    exact_index += 1
                    entry_ts = _adaptive_crossing_ts(orb_func, start_ts, exact_ts, forward=False) or start_ts
                    exit_ts = _adaptive_crossing_ts(orb_func, exact_ts, end_ts, forward=True) or end_ts

                    for phase_name, ts in (
                        ("approaching", entry_ts),
                        ("exact", exact_ts),
                        ("separating", exit_ts),
                    ):
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        arc = _arc_at(dt, natal_sun_lon)
                        lon, lat = _solar_arc_body(natal_chart, body, arc)
                        jd = _to_jd(dt)
                        house_info = _solar_arc_house_info(jd, lon, lat, location, house_system)
                        phases.append(
                            {
                                "exact_index": exact_index,
                                "phase": phase_name,
                                "timestamp_utc": _from_ts_iso(ts),
                                "transit_house": house_info.get("house"),
                                "transit_sign": house_info.get("sign"),
                            }
                        )

                    transit_start = entry_ts if transit_start is None else min(transit_start, entry_ts)
                    transit_end = exit_ts if transit_end is None else max(transit_end, exit_ts)

                if phases:
                    start_iso = _from_ts_iso(transit_start)
                    end_iso = _from_ts_iso(transit_end)
                    arc_now = _arc_at(datetime.fromtimestamp(transit_start, tz=timezone.utc), natal_sun_lon)
                    lon_now, lat_now = _solar_arc_body(natal_chart, body, arc_now)
                    jd_now = _to_jd(datetime.fromtimestamp(transit_start, tz=timezone.utc))
                    transit_house = _solar_arc_house_info(jd_now, lon_now, lat_now, location, house_system)
                    events.append(
                        {
                            "transit": {
                                "body": body,
                                "house": transit_house.get("house"),
                                "sign": transit_house.get("sign"),
                            },
                            "natal": {
                                "body": target_name,
                                "house": natal_house["house"],
                                "sign": natal_house["sign"],
                            },
                            "aspect": aspect_deg,
                            "transit_start": start_iso,
                            "transit_end": end_iso,
                            "phases": phases,
                        }
                    )

    events.sort(key=lambda item: item["transit_start"])

    return {
        "meta": {
            "start_utc": start_dt.isoformat().replace("+00:00", "Z"),
            "end_utc": end_dt.isoformat().replace("+00:00", "Z"),
        },
        "events": events,
    }
