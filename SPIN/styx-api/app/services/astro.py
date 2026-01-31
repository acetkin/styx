from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

from app.config import (
    ASTEROID_ORDER,
    ASPECT_ANGLES,
    ASPECT_CLASSES,
    ASPECT_ORBS,
    ASPECT_SET,
    DEFAULT_STAR_ORB,
    DEFAULT_FIXED_STARS,
    HOUSE_SYSTEM_MAP,
    PLANET_ORDER,
    SIGNS,
)

try:
    import swisseph as swe

    SWE_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when swisseph missing
    swe = None
    SWE_AVAILABLE = False

try:  # pragma: no cover - optional dependency for local timestamps
    from timezonefinder import TimezoneFinder

    _TZ_FINDER = TimezoneFinder()
except Exception:  # pragma: no cover
    _TZ_FINDER = None

REQUIRED_EPHE_FILES = {
    "sepl_18.se1",
    "semo_18.se1",
    "seas_18.se1",
    "sefstars.txt",
}

_EPHE_VALIDATED = False
_CITIES_CACHE: dict[Path, List[dict]] = {}
_COUNTRY_CACHE: dict[Path, dict[str, str]] = {}


BODY_IDS = {
    "sun": getattr(swe, "SUN", 0),
    "moon": getattr(swe, "MOON", 1),
    "mercury": getattr(swe, "MERCURY", 2),
    "venus": getattr(swe, "VENUS", 3),
    "mars": getattr(swe, "MARS", 4),
    "jupiter": getattr(swe, "JUPITER", 5),
    "saturn": getattr(swe, "SATURN", 6),
    "uranus": getattr(swe, "URANUS", 7),
    "neptune": getattr(swe, "NEPTUNE", 8),
    "pluto": getattr(swe, "PLUTO", 9),
}

ASTEROID_IDS = {
    "ceres": getattr(swe, "CERES", 0),
    "pallas": getattr(swe, "PALLAS", 0),
    "juno": getattr(swe, "JUNO", 0),
    "vesta": getattr(swe, "VESTA", 0),
    "chiron": getattr(swe, "CHIRON", 0),
    "lilith (black moon)": getattr(swe, "MEAN_APOG", 0),
    "lilith (asteroid)": getattr(swe, "AST_OFFSET", 0) + 1181,
}


def _parse_timestamp(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_julday(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000,
    )


def _resolve_timezone(lat: float, lon: float) -> str | None:
    if not _TZ_FINDER:
        return None
    try:
        return _TZ_FINDER.timezone_at(lat=lat, lng=lon)
    except Exception:
        return None


def _format_local_timestamp(dt_utc: datetime, tz_name: str | None) -> str | None:
    if not tz_name:
        return None
    try:
        return dt_utc.astimezone(ZoneInfo(tz_name)).isoformat()
    except Exception:
        return None


def _round_floats(value, ndigits: int = 2):
    if isinstance(value, float):
        return round(value, ndigits)
    if isinstance(value, list):
        return [_round_floats(item, ndigits) for item in value]
    if isinstance(value, dict):
        return {key: _round_floats(item, ndigits) for key, item in value.items()}
    return value


def round_payload(payload: dict, ndigits: int = 2) -> dict:
    return _round_floats(payload, ndigits)


def _default_aspect_config() -> tuple[str, List[float], Dict[float, float], Dict[float, str]]:
    return ASPECT_SET, ASPECT_ANGLES, ASPECT_ORBS, ASPECT_CLASSES


def _normalize_deg(value: float) -> float:
    return value % 360.0


def _normalize_signed_deg(value: float) -> float:
    return ((value + 180.0) % 360.0) - 180.0


def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def _sign_info(lon: float) -> Tuple[str, float]:
    index = int(lon // 30)
    return SIGNS[index], lon % 30.0


def _body_like_from_lon_lat(lon: float, lat: float, speed: float, house: int) -> dict:
    lon = _normalize_deg(lon)
    sign, deg_in_sign = _sign_info(lon)
    return {
        "lon": lon,
        "lat": lat,
        "speed": speed,
        "retrograde": speed < 0,
        "sign": sign,
        "deg_in_sign": deg_in_sign,
        "house": house,
    }


def _stub_body(house: int = 1) -> dict:
    return _body_like_from_lon_lat(0.0, 0.0, 0.0, house)


def _angle_payload(lon: float) -> dict:
    lon = _normalize_deg(lon)
    sign, deg_in_sign = _sign_info(lon)
    return {
        "lon": lon,
        "sign": sign,
        "deg_in_sign": deg_in_sign,
    }


def _resolve_ephe_path() -> Path | None:
    env_path = os.getenv("SE_EPHE_PATH")
    if env_path:
        env_candidate = Path(env_path)
        if env_candidate.exists():
            return env_candidate

    package_path = Path(__file__).resolve().parents[2] / "ephe"
    if package_path.exists():
        return package_path

    local_path = Path(__file__).resolve().parents[3] / "_local" / "ephe"
    if local_path.exists():
        return local_path

    if env_path:
        return Path(env_path)

    return None


def _ensure_ephe_path() -> Path:
    if not SWE_AVAILABLE:
        raise RuntimeError("swisseph_unavailable")

    ephe_path = _resolve_ephe_path()
    if not ephe_path:
        raise RuntimeError("SE_EPHE_PATH not set and default ephe path missing")
    if not ephe_path.exists():
        raise RuntimeError(f"SE_EPHE_PATH does not exist: {ephe_path}")

    swe.set_ephe_path(str(ephe_path))

    global _EPHE_VALIDATED
    if not _EPHE_VALIDATED:
        missing = [name for name in REQUIRED_EPHE_FILES if not (ephe_path / name).exists()]
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise RuntimeError(f"Missing Swiss Ephemeris data files: {missing_list}")
        _EPHE_VALIDATED = True

    return ephe_path


def _calc_body(jd: float, body_id: int, name: str) -> dict:
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    try:
        xx, _ = swe.calc_ut(jd, body_id, flags)
    except Exception as exc:
        raise RuntimeError(f"calc_failed:{name}") from exc

    lon = _normalize_deg(float(xx[0]))
    lat = float(xx[1])
    speed = float(xx[3]) if len(xx) > 3 else 0.0
    sign, deg_in_sign = _sign_info(lon)
    return {
        "lon": lon,
        "lat": lat,
        "speed": speed,
        "retrograde": speed < 0,
        "sign": sign,
        "deg_in_sign": deg_in_sign,
    }


def _calc_obliquity(jd: float) -> float:
    try:
        xx, _ = swe.calc_ut(jd, swe.ECL_NUT)
        return float(xx[0])
    except Exception as exc:
        raise RuntimeError("obliquity_calc_failed") from exc


def _calc_houses(
    jd: float,
    lat: float,
    lon: float,
    house_system: str,
) -> Tuple[Dict[str, float], float, float, float, bytes]:
    hsys = HOUSE_SYSTEM_MAP.get(house_system, "P")
    hsys_code = hsys.encode("ascii")

    try:
        cusps_list, ascmc = swe.houses(jd, lat, lon, hsys_code)
    except Exception as exc:
        raise RuntimeError("houses_calc_failed") from exc

    cusps = {str(i + 1): float(cusps_list[i]) for i in range(12)}
    asc = float(ascmc[0])
    mc = float(ascmc[1])
    armc = float(ascmc[2])
    return cusps, asc, mc, armc, hsys_code


def _calc_angles_for_location(
    jd: float,
    lat: float,
    lon: float,
    house_system: str,
) -> Dict[str, float]:
    cusps, asc, mc, armc, hsys = _calc_houses(jd, lat, lon, house_system)
    dsc = _normalize_deg(asc + 180.0)
    ic = _normalize_deg(mc + 180.0)
    return {"asc": asc, "dsc": dsc, "mc": mc, "ic": ic}


def _between(a: float, b: float, x: float) -> bool:
    if a <= b:
        return a <= x < b
    return x >= a or x < b


def _house_from_cusps(lon: float, cusps: Dict[str, float]) -> int:
    for i in range(1, 13):
        a = cusps[str(i)]
        b = cusps[str(1 if i == 12 else i + 1)]
        if _between(a, b, lon):
            return i
    return 1


def _assign_house(
    lon: float,
    lat: float,
    cusps: Dict[str, float],
    armc: float,
    geolat: float,
    hsys: bytes,
    eps: float,
) -> int:
    try:
        pos = swe.house_pos(armc, geolat, eps, hsys, lon, lat)
        house = int(pos)
        if house < 1:
            return 1
        if house > 12:
            return 12
        return house
    except Exception:
        pass
    return _house_from_cusps(lon, cusps)


def _calc_lots(is_day: bool, asc: float, sun: float, moon: float, saturn: float, venus: float, mars: float, jupiter: float) -> dict:
    def n(x: float) -> float:
        return _normalize_deg(x)

    if is_day:
        fortune = n(asc + moon - sun)
        spirit = n(asc + sun - moon)
        necessity = n(asc + saturn - fortune)
        love = n(asc + venus - spirit)
        courage = n(asc + mars - fortune)
        victory = n(asc + jupiter - spirit)
        nemesis = n(asc + saturn - sun)
    else:
        fortune = n(asc + sun - moon)
        spirit = n(asc + moon - sun)
        necessity = n(asc + fortune - saturn)
        love = n(asc + spirit - venus)
        courage = n(asc + fortune - mars)
        victory = n(asc + spirit - jupiter)
        nemesis = n(asc + sun - saturn)

    return {
        "fortune": {"lon": fortune},
        "spirit": {"lon": spirit},
        "necessity": {"lon": necessity},
        "love": {"lon": love},
        "courage": {"lon": courage},
        "victory": {"lon": victory},
        "nemesis": {"lon": nemesis},
    }


def _calc_star_conjunctions(
    jd: float,
    targets: List[Tuple[str, dict]],
    star_orb: float,
    warnings: List[str],
) -> List[dict]:
    results: List[dict] = []
    for star in DEFAULT_FIXED_STARS:
        try:
            res = swe.fixstar2_ut(star, jd)
            xx = res[0]
            star_lon = _normalize_deg(float(xx[0]))
            star_lat = float(xx[1])
        except Exception:
            warnings.append(f"star_calc_failed:{star}")
            continue

        for target_name, target in targets:
            orb = _angular_distance(star_lon, target["lon"])
            if orb <= star_orb:
                results.append(
                    {
                        "star": star,
                        "target": target_name,
                        "orb": orb,
                        "star_lon": star_lon,
                        "star_lat": star_lat,
                        "target_lon": target["lon"],
                    }
                )

    return results


def _aspect_delta(lon_a: float, lon_b: float, angle: float) -> float:
    delta = (lon_b - lon_a) % 360.0
    d1 = _normalize_signed_deg(delta - angle)
    if angle in (0.0, 180.0):
        return d1
    d2 = _normalize_signed_deg(delta - (360.0 - angle))
    return d1 if abs(d1) <= abs(d2) else d2


def _calc_aspects(
    targets: List[Tuple[str, dict]],
    angles: List[float],
    orbs: Dict[float, float],
    classes: Dict[float, str],
) -> List[dict]:
    results: List[dict] = []
    for i in range(len(targets)):
        a_name, a = targets[i]
        for j in range(i + 1, len(targets)):
            b_name, b = targets[j]
            lon_a = a["lon"]
            lon_b = b["lon"]
            speed_a = float(a.get("speed", 0.0))
            speed_b = float(b.get("speed", 0.0))
            rel_speed = speed_b - speed_a

            for angle in angles:
                d = _aspect_delta(lon_a, lon_b, angle)
                orb = abs(d)
                if orb <= orbs[angle]:
                    applying = False
                    separating = False
                    if rel_speed != 0.0 and d != 0.0:
                        applying = (d * rel_speed) < 0
                        separating = (d * rel_speed) > 0
                    results.append(
                        {
                            "a": a_name,
                            "b": b_name,
                            "type": classes.get(angle, "major"),
                            "exact_angle": str(int(angle)),
                            "orb": orb,
                            "applying": applying,
                            "separating": separating,
                        }
                    )
    return results


def _calc_cross_aspects(
    targets_a: List[Tuple[str, dict]],
    targets_b: List[Tuple[str, dict]],
    angles: List[float],
    orbs: Dict[float, float],
    classes: Dict[float, str],
    prefix_a: str,
    prefix_b: str,
) -> List[dict]:
    results: List[dict] = []
    for a_name, a in targets_a:
        for b_name, b in targets_b:
            if a_name.startswith("lot_") or b_name.startswith("lot_"):
                continue
            lon_a = a["lon"]
            lon_b = b["lon"]
            speed_a = float(a.get("speed", 0.0))
            speed_b = float(b.get("speed", 0.0))
            rel_speed = speed_b - speed_a
            for angle in angles:
                d = _aspect_delta(lon_a, lon_b, angle)
                orb = abs(d)
                if orb <= orbs[angle]:
                    applying = False
                    separating = False
                    if rel_speed != 0.0 and d != 0.0:
                        applying = (d * rel_speed) < 0
                        separating = (d * rel_speed) > 0
                    results.append(
                        {
                            "a": f"{prefix_a}{a_name}",
                            "b": f"{prefix_b}{b_name}",
                            "type": classes.get(angle, "major"),
                            "exact_angle": str(int(angle)),
                            "orb": orb,
                            "applying": applying,
                            "separating": separating,
                        }
                    )
    return results


def _build_aspect_targets(chart: dict) -> List[Tuple[str, dict]]:
    targets: List[Tuple[str, dict]] = []
    bodies = chart["bodies"]
    asteroids = chart.get("asteroids", {})
    angles = chart["angles"]
    points = chart["points"]

    for name in PLANET_ORDER:
        if name in bodies:
            targets.append((name, bodies[name]))
    for name in ASTEROID_ORDER:
        if name in asteroids:
            targets.append((name, asteroids[name]))
    for name in ("asc", "dsc", "mc", "ic"):
        if name in angles:
            targets.append((name, {"lon": angles[name]["lon"], "speed": 0.0}))
    if "nn" in points:
        targets.append(("nn", points["nn"]))
    if "sn" in points:
        targets.append(("sn", points["sn"]))
    if "lilith (black moon)" in points:
        targets.append(("lilith (black moon)", points["lilith (black moon)"]))
    return targets


def _load_cities(path: Path) -> List[dict]:
    if path in _CITIES_CACHE:
        return _CITIES_CACHE[path]
    if not path.exists():
        raise RuntimeError(f"cities_not_found:{path}")
    cities: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) < 9:
                continue
            try:
                lat = float(parts[4])
                lon = float(parts[5])
            except Exception:
                continue
            name = parts[1]
            country = parts[8]
            population = 0
            if len(parts) > 14:
                try:
                    population = int(parts[14])
                except Exception:
                    population = 0
            cities.append(
                {
                    "city": name,
                    "country": country,
                    "lat": lat,
                    "lon": lon,
                    "population": population,
                }
            )
    _CITIES_CACHE[path] = cities
    return cities


def _load_country_map(path: Path) -> dict[str, str]:
    if path in _COUNTRY_CACHE:
        return _COUNTRY_CACHE[path]
    if not path.exists():
        raise RuntimeError(f"countries_not_found:{path}")
    mapping: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) < 5:
                continue
            code = parts[0]
            name = parts[4]
            if code and name:
                mapping[code] = name
    _COUNTRY_CACHE[path] = mapping
    return mapping


def calc_astrocartography(
    frame_chart: dict,
    house_system: str,
    top_n: int = 50,
    cities_path: Path | None = None,
) -> dict:
    _ensure_ephe_path()

    dt_utc = _parse_timestamp(frame_chart["meta"]["timestamp_utc"])
    jd = _to_julday(dt_utc)

    path = cities_path
    if path is None:
        env_path = os.getenv("STYX_CITIES_PATH")
        if env_path:
            path = Path(env_path)
        else:
            path = Path(__file__).resolve().parents[2] / "data" / "cities5000.txt"

    country_path = os.getenv("STYX_COUNTRIES_PATH")
    if country_path:
        country_path = Path(country_path)
    else:
        country_path = Path(__file__).resolve().parents[2] / "data" / "countryInfo.txt"

    cities = _load_cities(path)
    try:
        country_map = _load_country_map(Path(country_path))
    except RuntimeError:
        country_map = {}

    body_lons = {}
    for name in PLANET_ORDER:
        if name in frame_chart["bodies"]:
            body_lons[name] = float(frame_chart["bodies"][name]["lon"])

    points = frame_chart.get("points", {})
    crossing_lons = dict(body_lons)
    if "nn" in points:
        crossing_lons["nn"] = float(points["nn"]["lon"])
    if "sn" in points:
        crossing_lons["sn"] = float(points["sn"]["lon"])

    max_orb = float(os.getenv("STYX_ASTRO_MAX_ORB", "2.0"))
    cross_top_n = int(os.getenv("STYX_ASTRO_CROSS_TOP_N", "50"))

    results: List[dict] = []
    crossings: List[dict] = []
    for city in cities:
        try:
            angles = _calc_angles_for_location(jd, city["lat"], city["lon"], house_system)
        except RuntimeError:
            continue

        line_hits: List[dict] = []
        for body_name, body_lon in crossing_lons.items():
            for angle_name, angle_lon in angles.items():
                orb = _angular_distance(body_lon, angle_lon)
                if orb <= max_orb:
                    line_hits.append(
                        {
                            "body": body_name,
                            "angle_line": angle_name,
                            "orb": orb,
                        }
                    )

        for body_name, body_lon in body_lons.items():
            for angle_name, angle_lon in angles.items():
                orb = _angular_distance(body_lon, angle_lon)
                if orb > max_orb:
                    continue
                country_name = country_map.get(city["country"], city["country"])
                results.append(
                    {
                        "body": body_name,
                        "angle_line": angle_name,
                        "city": city["city"],
                        "country": country_name,
                        "lat": city["lat"],
                        "lon": city["lon"],
                        "orb": orb,
                        "population": city["population"],
                    }
                )

        if len(line_hits) > 1:
            for i in range(len(line_hits)):
                for j in range(i + 1, len(line_hits)):
                    a = line_hits[i]
                    b = line_hits[j]
                    if a["body"] == b["body"] and a["angle_line"] == b["angle_line"]:
                        continue
                    country_name = country_map.get(city["country"], city["country"])
                    crossings.append(
                        {
                            "a_body": a["body"],
                            "a_line": a["angle_line"],
                            "a_orb": a["orb"],
                            "b_body": b["body"],
                            "b_line": b["angle_line"],
                            "b_orb": b["orb"],
                            "city": city["city"],
                            "country": country_name,
                            "lat": city["lat"],
                            "lon": city["lon"],
                            "population": city["population"],
                        }
                    )

    results.sort(key=lambda item: (item["orb"], -item["population"], item["city"]))
    trimmed = results[: max(top_n, 0)]
    for item in trimmed:
        item.pop("population", None)
    crossings.sort(key=lambda item: (max(item["a_orb"], item["b_orb"]), -item["population"], item["city"]))
    cross_trimmed = crossings[: max(cross_top_n, 0)]
    for item in cross_trimmed:
        item.pop("population", None)
    return {"results": trimmed, "crossings": cross_trimmed}


def calc_chart(
    chart_type: str,
    timestamp_utc: str,
    location: dict,
    settings,
    round_output: bool = True,
) -> dict:
    warnings: List[str] = []

    _ensure_ephe_path()

    dt_utc = _parse_timestamp(timestamp_utc)
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000,
    )

    cusps, asc, mc, armc, hsys = _calc_houses(jd, location["lat"], location["lon"], settings.house_system)
    dsc = _normalize_deg(asc + 180.0)
    ic = _normalize_deg(mc + 180.0)

    eps = _calc_obliquity(jd)

    bodies: Dict[str, dict] = {}
    for name in PLANET_ORDER:
        body = _calc_body(jd, BODY_IDS[name], name)
        body["house"] = _assign_house(body["lon"], body["lat"], cusps, armc, location["lat"], hsys, eps)
        bodies[name] = body

    asteroids: Dict[str, dict] = {}
    for name in ASTEROID_ORDER:
        try:
            body = _calc_body(jd, ASTEROID_IDS[name], name)
        except RuntimeError as exc:
            if name == "lilith (asteroid)":
                warnings.append(str(exc))
                body = _stub_body()
            else:
                raise
        body["house"] = _assign_house(body["lon"], body["lat"], cusps, armc, location["lat"], hsys, eps)
        asteroids[name] = body

    nn = _calc_body(jd, getattr(swe, "TRUE_NODE", 0), "true_node")
    nn["house"] = _assign_house(nn["lon"], nn["lat"], cusps, armc, location["lat"], hsys, eps)

    sn_lon = _normalize_deg(nn["lon"] + 180.0)
    sn_lat = -nn["lat"]
    sn_house = _assign_house(sn_lon, sn_lat, cusps, armc, location["lat"], hsys, eps)
    sn = _body_like_from_lon_lat(sn_lon, sn_lat, nn["speed"], sn_house)

    sun_lon = bodies["sun"]["lon"]
    moon_lon = bodies["moon"]["lon"]
    saturn_lon = bodies["saturn"]["lon"]
    venus_lon = bodies["venus"]["lon"]
    mars_lon = bodies["mars"]["lon"]
    jupiter_lon = bodies["jupiter"]["lon"]
    is_day = bodies["sun"]["house"] >= 7

    lots_raw = _calc_lots(is_day, asc, sun_lon, moon_lon, saturn_lon, venus_lon, mars_lon, jupiter_lon)
    lots = {}
    for name, payload in lots_raw.items():
        lot_lon = payload["lon"]
        lot_house = _assign_house(lot_lon, 0.0, cusps, armc, location["lat"], hsys, eps)
        lots[name] = _body_like_from_lon_lat(lot_lon, 0.0, 0.0, lot_house)

    lilith_mode = "mean"
    points_settings = getattr(settings, "points", None)
    if points_settings and points_settings.lilith:
        lilith_mode = points_settings.lilith
    lilith_id = swe.MEAN_APOG if lilith_mode == "mean" else swe.OSCU_APOG
    lilith = _calc_body(jd, lilith_id, f"lilith_{lilith_mode}")
    lilith["house"] = _assign_house(lilith["lon"], lilith["lat"], cusps, armc, location["lat"], hsys, eps)

    angles = {
        "asc": _angle_payload(asc),
        "dsc": _angle_payload(dsc),
        "mc": _angle_payload(mc),
        "ic": _angle_payload(ic),
    }

    cusps_out = {str(i): _angle_payload(cusps[str(i)]) for i in range(1, 13)}

    targets = [(name, bodies[name]) for name in PLANET_ORDER] + [(name, asteroids[name]) for name in ASTEROID_ORDER]
    targets.extend((name, angles[name]) for name in ("asc", "dsc", "mc", "ic"))
    targets.extend((name, nn) for name in ("nn",))
    targets.extend((name, sn) for name in ("sn",))
    targets.extend((f"lot_{name}", lots[name]) for name in sorted(lots.keys()))
    if lilith is not None:
        targets.append(("lilith (black moon)", lilith))
    stars = _calc_star_conjunctions(jd, targets, DEFAULT_STAR_ORB, warnings)

    aspect_set, aspect_angles, aspect_orbs, aspect_classes = _default_aspect_config()

    tz_name = _resolve_timezone(location["lat"], location["lon"])
    timestamp_local = _format_local_timestamp(dt_utc, tz_name)
    if tz_name and not timestamp_local:
        tz_name = None
    meta = {
        "output_type": chart_type,
        "mode": "chart",
        "chart_type": chart_type,
        "timestamp_utc": dt_utc.isoformat(),
        "timestamp_local": timestamp_local,
        "timezone": tz_name,
        "location": {
            "lat": location["lat"],
            "lon": location["lon"],
            "alt_m": location.get("alt_m", 0),
            "place": location.get("place"),
        },
    }
    if warnings:
        meta["warnings"] = warnings

    points_out = {"nn": nn, "sn": sn, "lots": lots, "lilith (black moon)": lilith}

    aspect_targets: List[Tuple[str, dict]] = []
    for name in PLANET_ORDER:
        aspect_targets.append((name, bodies[name]))
    for name in ASTEROID_ORDER:
        aspect_targets.append((name, asteroids[name]))
    for name in ("asc", "dsc", "mc", "ic"):
        aspect_targets.append((name, {"lon": angles[name]["lon"], "speed": 0.0}))
    aspect_targets.append(("nn", nn))
    aspect_targets.append(("sn", sn))
    aspect_targets.append(("lilith (black moon)", lilith))
    aspects = _calc_aspects(aspect_targets, aspect_angles, aspect_orbs, aspect_classes)

    response = {
        "meta": meta,
        "angles": angles,
        "houses": {"system": settings.house_system, "cusps": cusps_out},
        "bodies": bodies,
        "asteroids": asteroids,
        "points": points_out,
        "aspects": aspects,
        "stars": stars,
    }
    if round_output:
        return _round_floats(response, 2)
    return response


def get_provenance() -> dict:
    if SWE_AVAILABLE:
        sw_version = getattr(swe, "version", "unknown")
        if callable(sw_version):
            try:
                sw_version = sw_version()
            except Exception:
                sw_version = "unknown"
    else:
        sw_version = "unavailable"
    return {"swisseph_version": sw_version, "flags": {"topocentric": False}}
