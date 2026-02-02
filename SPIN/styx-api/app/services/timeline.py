from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

import swisseph as swe

from app.config import ASPECT_ANGLES, PLANET_ORDER, ASTEROID_ORDER, TRANSIT_ORB_TABLE, SIGNS
from app.services.astro import (
    _aspect_delta,
    _calc_body,
    _calc_houses,
    _assign_house,
    _calc_obliquity,
    _ensure_ephe_path,
    _normalize_deg,
    _parse_timestamp,
)

ASPECT_DEG = {
    0.0: "0",
    60.0: "60",
    90.0: "90",
    120.0: "120",
    180.0: "180",
}

LEVEL_BODIES = {
    "level1": ["uranus", "neptune", "pluto"],
    "level2": ["saturn", "jupiter"],
    "outer": ["uranus", "neptune", "pluto"],
    "jupiter": ["jupiter"],
    "saturn": ["saturn"],
    "uranus": ["uranus"],
    "neptune": ["neptune"],
    "pluto": ["pluto"],
    "nodes": ["nn", "sn"],
}

BODY_ID = {
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
    "nn": swe.TRUE_NODE,
}

STEP_DAYS = {
    "jupiter": 3.0,
    "saturn": 3.0,
    "uranus": 5.0,
    "neptune": 5.0,
    "pluto": 5.0,
    "nn": 2.0,
    "sn": 2.0,
}
STEP_SCHEDULE_DAYS = [30.0, 7.0, 1.0, 1.0 / 24.0, 1.0 / 1440.0]


@dataclass(frozen=True)
class Station:
    jd: float
    kind: str  # "R" or "D"


def _to_jd(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000,
    )


def _from_jd(jd: float) -> datetime:
    year, month, day, ut = swe.revjul(jd)
    base = datetime(year, month, day, tzinfo=timezone.utc)
    return base + timedelta(hours=ut)


def _from_jd_iso(jd: float) -> str:
    ts = _from_jd(jd)
    return ts.isoformat().replace("+00:00", "Z")


def _sign_for_lon(lon: float) -> str:
    idx = int(_normalize_deg(lon) // 30)
    return SIGNS[idx]


def _house_sign(cusps: Dict[str, float], house: int) -> str:
    return _sign_for_lon(cusps[str(house)])


def _body_position(jd: float, body_key: str) -> Tuple[float, float, float]:
    if body_key == "sn":
        nn = _calc_body(jd, BODY_ID["nn"], "nn")
        lon = _normalize_deg(nn["lon"] + 180.0)
        lat = -nn["lat"]
        speed = -nn["speed"]
        return lon, lat, speed
    body_id = BODY_ID[body_key]
    body = _calc_body(jd, body_id, body_key)
    return body["lon"], body["lat"], body["speed"]


def _speed(jd: float, body_key: str) -> float:
    if body_key == "sn":
        nn = _calc_body(jd, BODY_ID["nn"], "nn")
        return -nn["speed"]
    body_id = BODY_ID[body_key]
    body = _calc_body(jd, body_id, body_key)
    return body["speed"]


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


def _scan_brackets(func, start_jd: float, end_jd: float, step_days: float) -> list[tuple[float, float]]:
    brackets: list[tuple[float, float]] = []
    t = start_jd
    prev = func(t)
    while t < end_jd:
        t_next = min(t + step_days, end_jd)
        cur = func(t_next)
        if prev == 0:
            brackets.append((t, t))
        elif prev * cur <= 0:
            brackets.append((t, t_next))
        prev = cur
        t = t_next
    return brackets


def _adaptive_roots(func, start_jd: float, end_jd: float) -> list[float]:
    brackets = [(start_jd, end_jd)]
    for step_days in STEP_SCHEDULE_DAYS:
        refined: list[tuple[float, float]] = []
        for a, b in brackets:
            refined.extend(_scan_brackets(func, a, b, step_days))
        brackets = refined
        if not brackets:
            return []
    roots: list[float] = []
    for a, b in brackets:
        roots.append(_find_root(func, a, b))
    return sorted({round(r, 6) for r in roots})


def _adaptive_crossing(func, start_jd: float, end_jd: float, forward: bool) -> float | None:
    if start_jd == end_jd:
        return start_jd
    brackets = [(start_jd, end_jd)]
    for step_days in STEP_SCHEDULE_DAYS:
        refined: list[tuple[float, float]] = []
        for a, b in brackets:
            refined.extend(_scan_brackets(func, a, b, step_days))
        if refined:
            brackets = refined
        if not brackets:
            return None
    chosen = brackets[0] if forward else brackets[-1]
    return _find_root(func, chosen[0], chosen[1])


def _find_stations(body_key: str, start_jd: float, end_jd: float) -> List[Station]:
    step = STEP_DAYS[body_key]
    stations: List[Station] = []
    jd = start_jd
    prev_speed = _speed(jd, body_key)
    jd += step
    while jd <= end_jd:
        speed = _speed(jd, body_key)
        if prev_speed == 0:
            prev_speed = speed
        if speed == 0:
            kind = "R" if prev_speed > 0 else "D"
            stations.append(Station(jd=jd, kind=kind))
        elif (prev_speed > 0 and speed < 0) or (prev_speed < 0 and speed > 0):
            kind = "R" if prev_speed > 0 else "D"
            root = _find_root(lambda t: _speed(t, body_key), jd - step, jd)
            stations.append(Station(jd=root, kind=kind))
        prev_speed = speed
        jd += step
    stations.sort(key=lambda s: s.jd)
    return stations


def _natal_targets(natal_chart: dict) -> List[Tuple[str, dict]]:
    targets: List[Tuple[str, dict]] = []

    bodies = natal_chart.get("bodies", {})
    asteroids = natal_chart.get("asteroids", {})
    angles = natal_chart.get("angles", {})
    points = natal_chart.get("points", {})

    for name in PLANET_ORDER:
        if name in bodies:
            targets.append((name, bodies[name]))
    for name in ASTEROID_ORDER:
        if name in asteroids:
            targets.append((name, asteroids[name]))
    for name in ("asc", "dsc", "mc", "ic"):
        if name in angles:
            targets.append((name, angles[name]))
    for name in ("nn", "sn"):
        if name in points:
            targets.append((name, points[name]))

    return targets


def _target_house_info(natal_chart: dict, target_name: str) -> dict:
    cusps = natal_chart["houses"]["cusps"]
    if target_name == "asc":
        house = 1
    elif target_name == "dsc":
        house = 7
    elif target_name == "mc":
        house = 10
    elif target_name == "ic":
        house = 4
    else:
        if target_name in natal_chart.get("bodies", {}):
            house = natal_chart["bodies"][target_name]["house"]
        elif target_name in natal_chart.get("asteroids", {}):
            house = natal_chart["asteroids"][target_name]["house"]
        else:
            house = natal_chart["points"][target_name]["house"]
    return {"house": house, "sign": cusps[str(house)]["sign"]}


def _transit_house_info(jd: float, lon: float, lat: float, location: dict, house_system: str) -> dict:
    cusps, _, _, armc, hsys = _calc_houses(jd, location["lat"], location["lon"], house_system)
    eps = _calc_obliquity(jd)
    house = _assign_house(lon, lat, cusps, armc, location["lat"], hsys, eps)
    return {"house": house, "sign": _house_sign(cusps, house)}


def _station_tag(stations: List[Station], jd: float) -> str | None:
    for station in stations:
        if abs(station.jd - jd) < 1e-4:
            return station.kind
    return None


def build_timeline(
    natal_chart: dict,
    start_utc: str,
    end_utc: str,
    level: str,
    house_system: str,
    bodies: List[str] | None = None,
) -> dict:
    _ensure_ephe_path()
    start_dt = _parse_timestamp(start_utc)
    end_dt = _parse_timestamp(end_utc)
    start_jd = _to_jd(start_dt)
    end_jd = _to_jd(end_dt)

    targets = _natal_targets(natal_chart)
    location = natal_chart["meta"]["location"]

    events: List[dict] = []

    if bodies is None:
        bodies = LEVEL_BODIES[level]

    for transit_body in bodies:
        orb = TRANSIT_ORB_TABLE["nodes"] if transit_body in {"nn", "sn"} else TRANSIT_ORB_TABLE[transit_body]
        stations = _find_stations("nn" if transit_body == "sn" else transit_body, start_jd, end_jd)

        for target_name, target in targets:
            target_lon = target["lon"]
            natal_house = _target_house_info(natal_chart, target_name)

            for angle in (0.0, 60.0, 90.0, 120.0, 180.0):
                aspect_name = ASPECT_DEG[angle]
                exact_index = 0
                phases: List[dict] = []
                first_transit_house = None
                transit_start = None
                transit_end = None

                def delta(jd: float) -> float:
                    lon, _, _ = _body_position(jd, transit_body)
                    return _aspect_delta(lon, target_lon, angle)

                def orb_func(jd: float) -> float:
                    lon, _, _ = _body_position(jd, transit_body)
                    return abs(_aspect_delta(lon, target_lon, angle)) - orb

                exact_jds = _adaptive_roots(delta, start_jd, end_jd)
                for exact_jd in exact_jds:
                    exact_index += 1

                    entry = _adaptive_crossing(orb_func, start_jd, exact_jd, forward=False) or start_jd
                    exit_ = _adaptive_crossing(orb_func, exact_jd, end_jd, forward=True) or end_jd

                    for phase_name, jd in (
                        ("approaching", entry),
                        ("exact", exact_jd),
                        ("separating", exit_),
                    ):
                        lon, lat, _ = _body_position(jd, transit_body)
                        transit_house = _transit_house_info(jd, lon, lat, location, house_system)
                        station_tag = _station_tag(stations, jd)
                        if station_tag:
                            transit_house = {**transit_house, "transit_station": station_tag}
                        if first_transit_house is None and phase_name in {"approaching", "exact"}:
                            first_transit_house = transit_house
                        phases.append(
                            {
                                "exact_index": exact_index,
                                "phase": phase_name,
                                "timestamp_utc": _from_jd_iso(jd),
                                "transit_station": transit_house.get("transit_station"),
                            }
                        )

                    transit_start = entry if transit_start is None else min(transit_start, entry)
                    transit_end = exit_ if transit_end is None else max(transit_end, exit_)

                if phases:
                    if first_transit_house is None:
                        first_transit_house = {"house": None, "sign": None}
                    events.append(
                        {
                            "transit": {
                                "body": transit_body,
                                "house": first_transit_house.get("house"),
                                "sign": first_transit_house.get("sign"),
                            },
                            "natal": {
                                "body": target_name,
                                "house": natal_house["house"],
                                "sign": natal_house["sign"],
                            },
                            "aspect": aspect_name,
                            "transit_start": _from_jd_iso(transit_start),
                            "transit_end": _from_jd_iso(transit_end),
                            "phases": phases,
                        }
                    )

    events.sort(key=lambda item: item["transit_start"])

    return {
        "meta": {
            "start_utc": start_dt.isoformat().replace("+00:00", "Z"),
            "end_utc": end_dt.isoformat().replace("+00:00", "Z"),
            "level": level,
        },
        "events": events,
    }
