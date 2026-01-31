from __future__ import annotations

from pathlib import Path
import time
import json

from fastapi.testclient import TestClient

from app.config import (
    ASTEROID_ORDER,
    DEFAULT_COORDINATE_SYSTEM,
    DEFAULT_FIXED_STARS,
    DEFAULT_HOUSE_SYSTEM,
    DEFAULT_STAR_ORB,
    DEFAULT_ZODIAC,
    PLANET_ORDER,
)
from app.main import app


def _client(monkeypatch: object) -> TestClient:
    ephe_path = Path(__file__).resolve().parents[1] / "ephe"
    if ephe_path.exists():
        monkeypatch.setenv("SE_EPHE_PATH", str(ephe_path))
    monkeypatch.setenv("STYX_GEOCODE_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")
    monkeypatch.setenv("STYX_GEOIP_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")
    cities_path = Path(__file__).resolve().parent / "fixtures" / "cities.txt"
    if cities_path.exists():
        monkeypatch.setenv("STYX_CITIES_PATH", str(cities_path))
    countries_path = Path(__file__).resolve().parent / "fixtures" / "countries.txt"
    if countries_path.exists():
        monkeypatch.setenv("STYX_COUNTRIES_PATH", str(countries_path))
    return TestClient(app)


def _measure(client: TestClient, method: str, url: str, **kwargs) -> tuple[float, object]:
    start = time.perf_counter()
    resp = client.request(method, url, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000.0
    return duration_ms, resp


def _write_latency_log(data: dict) -> None:
    try:
        log_dir = Path(__file__).resolve().parents[2] / "_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "latency_test.json"
        payload = {}
        if log_path.exists():
            try:
                payload = json.loads(log_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        payload.update(data)
        log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def test_health(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    ms, resp = _measure(client, "GET", "/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    _write_latency_log({"health_ms": ms})


def test_config(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    ms, resp = _measure(client, "GET", "/v1/config")
    assert resp.status_code == 200
    payload = resp.json()

    defaults = payload["defaults"]
    assert defaults["house_system"] == DEFAULT_HOUSE_SYSTEM
    assert defaults["zodiac"] == DEFAULT_ZODIAC
    assert defaults["coordinate_system"] == DEFAULT_COORDINATE_SYSTEM
    assert defaults["star_orb"] == DEFAULT_STAR_ORB
    assert defaults["points"]["lilith"] == "mean"

    catalogs = payload["catalogs"]
    assert catalogs["planets"] == PLANET_ORDER
    assert catalogs["asteroids"] == ASTEROID_ORDER
    assert catalogs["fixed_stars"] == DEFAULT_FIXED_STARS

    provenance = payload["provenance"]
    assert "swisseph_version" in provenance
    assert provenance["flags"]["topocentric"] is False

    aspects = payload["aspects"]
    assert aspects["set"] == "major_minor"
    assert aspects["orbs"]["0"] == 8.0
    assert aspects["orbs"]["30"] == 6.0
    assert aspects["orbs"]["45"] == 6.0
    assert aspects["orbs"]["60"] == 6.0
    assert aspects["orbs"]["72"] == 6.0
    assert aspects["orbs"]["90"] == 6.0
    assert aspects["orbs"]["120"] == 6.0
    assert aspects["orbs"]["135"] == 6.0
    assert aspects["orbs"]["150"] == 6.0
    assert aspects["orbs"]["180"] == 8.0
    _write_latency_log({"config_ms": ms})


def test_chart_schema(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    ms, resp = _measure(
        client,
        "POST",
        "/v1/chart",
        json={
            "metadata": {
                "chart_type": "natal",
                "timestamp_utc": "1982-05-08T06:39:00+03:00",
                "location": "Karadeniz Eregli",
            },
            "settings": {
                "house_system": "placidus",
                "zodiac": "tropical",
                "coordinate_system": "ecliptic",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()

    for key in ("meta", "bodies", "asteroids", "angles", "houses", "points", "aspects", "stars"):
        assert key in payload
    assert "name" in payload["meta"]

    for angle in ("asc", "dsc", "mc", "ic"):
        assert set(payload["angles"][angle].keys()) == {"lon", "sign", "deg_in_sign"}

    cusps = payload["houses"]["cusps"]
    assert len(cusps) == 12
    assert set(cusps["1"].keys()) == {"lon", "sign", "deg_in_sign"}

    for field in ("lon", "lat", "speed", "retrograde", "sign", "deg_in_sign", "house"):
        assert field in payload["points"]["nn"]
        assert field in payload["points"]["sn"]
        assert field in payload["points"]["lots"]["fortune"]
        assert field in payload["points"]["lilith (black moon)"]

    assert "timezone" in payload["meta"]
    assert "timestamp_local" in payload["meta"]
    if payload["meta"]["timezone"]:
        assert payload["meta"]["timestamp_local"]

    if payload["aspects"]:
        sample = payload["aspects"][0]
        for field in ("a", "b", "type", "exact_angle", "orb", "applying", "separating"):
            assert field in sample
        assert sample["type"] in {"major", "minor"}
        assert isinstance(sample["exact_angle"], str)
    _write_latency_log({"chart_ms": ms})


def test_chart_lilith_enabled(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/chart",
        json={
            "metadata": {
                "chart_type": "natal",
                "timestamp_utc": "1982-05-08T06:39:00+03:00",
                "location": "Karadeniz Eregli",
            },
            "settings": {
                "house_system": "placidus",
                "zodiac": "tropical",
                "coordinate_system": "ecliptic",
                "points": {"lilith": "true"},
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "lilith (black moon)" in payload["points"]


def test_transit_basic(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/transit",
        json={
            "metadata": {"transit_type": "transit"},
            "frame_a": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1982-05-08T06:39:00+03:00",
                    "location": "Karadeniz Eregli",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["transit_type"] == "transit"
    assert "aspects" in payload
    assert "frame_a" not in payload
    assert "frame_b" not in payload


def test_transit_modes(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    base_frame = {
        "metadata": {
            "chart_type": "natal",
            "timestamp_utc": "1982-05-08T06:39:00+03:00",
            "location": "Karadeniz Eregli",
        }
    }
    for transit_type in ("on_natal", "secondary_progression"):
        resp = client.post(
            "/v1/transit",
            json={
                "metadata": {
                    "transit_type": transit_type,
                    "timestamp_utc": "2026-01-28T10:00:00+03:00",
                    "location": "Karadeniz Eregli",
                },
                "frame_a": base_frame,
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["meta"]["transit_type"] == transit_type
        assert "aspects" in payload

    resp = client.post(
        "/v1/transit",
        json={
            "metadata": {"transit_type": "astrocartography"},
            "frame_a": base_frame,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["transit_type"] == "astrocartography"
    assert "results" in payload
    assert "crossings" in payload
    assert "aspects" not in payload
    assert payload["results"]
    assert any(item["country"] == "Turkey" for item in payload["results"])

    resp = client.post(
        "/v1/transit",
        json={
            "metadata": {
                "transit_type": "solar_arc",
                "timestamp_utc": "2026-01-28T10:00:00+03:00",
                "solar_arc_sun": "mean",
            },
            "frame_a": base_frame,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["transit_type"] == "solar_arc"
    assert payload["meta"]["solar_arc_sun"] == "mean"
    assert "aspects" in payload

    resp = client.post(
        "/v1/transit",
        json={
            "metadata": {"transit_type": "synastry"},
            "frame_a": base_frame,
            "frame_b": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1985-02-12T10:15:00+03:00",
                    "location": "Istanbul",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["transit_type"] == "synastry"
    assert "aspects" in payload


def test_timeline_basic(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/timeline",
        json={
            "metadata": {
                "start_utc": "2030-01-01T00:00:00Z",
                "end_utc": "2031-01-01T00:00:00Z",
                "level": "level1",
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1982-05-08T06:39:00+03:00",
                    "location": "Karadeniz Eregli",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["level"] == "level1"
    assert "events" in payload


def test_timeline_body_override(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/timeline",
        json={
            "metadata": {
                "start_utc": "2030-01-01T00:00:00Z",
                "end_utc": "2031-01-01T00:00:00Z",
                "level": "outer",
                "body": "uranus",
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1982-05-08T06:39:00+03:00",
                    "location": "Karadeniz Eregli",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["level"] == "outer"
    assert "events" in payload


def test_timeline_lunations(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/timeline",
        json={
            "metadata": {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2026-06-01T00:00:00Z",
                "level": "eclipses",
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1982-05-08T06:39:00+03:00",
                    "location": "Karadeniz Eregli",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["meta"]["level"] == "eclipses"
    assert "events" in payload


def test_progression_timeline(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/progression_timeline",
        json={
            "metadata": {
                "start_utc": "1982-05-08T03:39:00Z",
                "end_utc": "1983-05-08T03:39:00Z",
                "step_years": 1,
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "1982-05-08T06:39:00+03:00",
                    "location": "Karadeniz Eregli",
                }
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "events" in payload
    event = payload["events"][0]
    assert "transit" in event
    assert "natal" in event
    assert "aspect" in event
    assert "phases" in event
    assert event["transit"]["body"] not in {"uranus", "neptune", "pluto"}
