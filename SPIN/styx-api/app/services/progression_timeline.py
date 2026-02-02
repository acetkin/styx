from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Callable

import swisseph as swe

from app.config import PLANET_ORDER, PROGRESSION_ORB_DEFAULT, SIGNS, TRANSIT_ORB_TABLE
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

OUTER_EXCLUDE = {"uranus", "neptune", "pluto"}
ASPECT_ANGLES = [0.0, 60.0, 90.0, 120.0, 180.0]
ASPECT_DEG = {0.0: "0", 60.0: "60", 90.0: "90", 120.0: "120", 180.0: "180"}

ANGLE_KEYS = ("asc", "dsc", "mc", "ic")
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


def _progressed_jd(natal_dt: datetime, target_dt: datetime) -> float:
    delta_years = (target_dt - natal_dt).total_seconds() / (365.25 * 86400.0)
    progressed_dt = natal_dt + timedelta(days=delta_years)
    return _to_jd(progressed_dt)


def _sign_for_lon(lon: float) -> str:
    idx = int(_normalize_deg(lon) // 30)
    return SIGNS[idx]


def _station_flag(jd: float, body_id: int) -> str | None:
    try:
        pre = _calc_body(jd - 0.5, body_id, "tmp")
        post = _calc_body(jd + 0.5, body_id, "tmp")
    except Exception:
        return None
    s1 = pre.get("speed", 0.0)
    s2 = post.get("speed", 0.0)
    if s1 == 0 or s2 == 0:
        return None
    if s1 > 0 and s2 < 0:
        return "R"
    if s1 < 0 and s2 > 0:
        return "D"
    return None


def _natal_targets(natal_chart: dict) -> List[Tuple[str, dict]]:
    targets: List[Tuple[str, dict]] = []
    bodies = natal_chart.get("bodies", {})
    angles = natal_chart.get("angles", {})
    points = natal_chart.get("points", {})

    for name, payload in bodies.items():
        targets.append((name, payload))
    for name in ("asc", "dsc", "mc", "ic"):
        if name in angles:
            targets.append((name, {"lon": angles[name]["lon"], "house": None}))
    for name in ("nn", "sn"):
        if name in points:
            targets.append((name, points[name]))

    return targets


def _natal_house_info(natal_chart: dict, target_name: str) -> dict:
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
        else:
            house = natal_chart["points"][target_name]["house"]
    return {"house": house, "sign": cusps[str(house)]["sign"]}


def _progressed_context(jd: float, location: dict, house_system: str) -> Tuple[Dict[str, float], float, float, float, bytes]:
    cusps, asc, mc, armc, hsys = _calc_houses(jd, location["lat"], location["lon"], house_system)
    return cusps, asc, mc, armc, hsys


def _progressed_body_info(
    jd: float,
    name: str,
    location: dict,
    house_system: str,
) -> dict:
    cusps, asc, mc, armc, hsys = _progressed_context(jd, location, house_system)
    dsc = _normalize_deg(asc + 180.0)
    ic = _normalize_deg(mc + 180.0)
    eps = _calc_obliquity(jd)

    if name in ANGLE_KEYS:
        lon_map = {"asc": asc, "dsc": dsc, "mc": mc, "ic": ic}
        lon = lon_map[name]
        house_map = {"asc": 1, "dsc": 7, "mc": 10, "ic": 4}
        return {
            "lon": lon,
            "lat": 0.0,
            "house": house_map[name],
            "sign": _sign_for_lon(lon),
            "station": None,
        }

    body_id = getattr(swe, name.upper())
    body = _calc_body(jd, body_id, name)
    house = _assign_house(body["lon"], body["lat"], cusps, armc, location["lat"], hsys, eps)
    station = _station_flag(jd, body_id)
    return {
        "lon": body["lon"],
        "lat": body["lat"],
        "house": house,
        "sign": body["sign"],
        "station": station,
    }


def _find_root(func: Callable[[float], float], a: float, b: float, steps: int = 40) -> float:
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


def _scan_brackets_ts(func: Callable[[float], float], start_ts: float, end_ts: float, step_seconds: float) -> list[tuple[float, float]]:
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


def _adaptive_roots_ts(func: Callable[[float], float], start_ts: float, end_ts: float) -> list[float]:
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
        roots.append(_find_root(func, a, b))
    return sorted({round(r, 6) for r in roots})


def _adaptive_crossing_ts(func: Callable[[float], float], start_ts: float, end_ts: float, forward: bool) -> float | None:
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


def build_progression_timeline(
    natal_chart: dict,
    start_utc: str,
    end_utc: str,
) -> dict:
    _ensure_ephe_path()
    natal_dt = _parse_timestamp(natal_chart["meta"]["timestamp_utc"])
    start_dt = _parse_timestamp(start_utc)
    end_dt = _parse_timestamp(end_utc)

    location = natal_chart["meta"]["location"]
    house_system = natal_chart["houses"]["system"]

    targets = _natal_targets(natal_chart)

    progressed_bodies = [name for name in PLANET_ORDER if name not in OUTER_EXCLUDE]
    progressed_angles = list(ANGLE_KEYS)

    events: List[dict] = []

    for prog_body in progressed_bodies + progressed_angles:
        orb = TRANSIT_ORB_TABLE.get(prog_body, PROGRESSION_ORB_DEFAULT)

        def lon_at(target_dt: datetime) -> Tuple[float, str | None, dict]:
            jd = _progressed_jd(natal_dt, target_dt)
            info = _progressed_body_info(jd, prog_body, location, house_system)
            return info["lon"], info.get("station"), info

        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()

        for target_name, target in targets:
            target_lon = target["lon"]
            natal_house = _natal_house_info(natal_chart, target_name)

            for angle in ASPECT_ANGLES:
                aspect_deg = ASPECT_DEG[angle]
                exact_index = 0
                phases: List[dict] = []
                transit_start = None
                transit_end = None

                def delta_at(ts: float) -> float:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    lon, _, _ = lon_at(dt)
                    return _aspect_delta(lon, target_lon, angle)

                def orb_func(ts: float) -> float:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    lon, _, _ = lon_at(dt)
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
                        _, station, _ = lon_at(dt)
                        payload = {
                            "exact_index": exact_index,
                            "phase": phase_name,
                            "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                        }
                        if station:
                            payload["transit_station"] = station
                        phases.append(payload)

                    transit_start = entry_ts if transit_start is None else min(transit_start, entry_ts)
                    transit_end = exit_ts if transit_end is None else max(transit_end, exit_ts)

                if phases:
                    start_iso = datetime.fromtimestamp(transit_start, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                    end_iso = datetime.fromtimestamp(transit_end, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                    transit_info = _progressed_body_info(
                        _progressed_jd(natal_dt, datetime.fromtimestamp(transit_start, tz=timezone.utc)),
                        prog_body,
                        location,
                        house_system,
                    )
                    events.append(
                        {
                            "transit": {
                                "body": prog_body,
                                "house": transit_info["house"],
                                "sign": transit_info["sign"],
                                "station": transit_info.get("station"),
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
