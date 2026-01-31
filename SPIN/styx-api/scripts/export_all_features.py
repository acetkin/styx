import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

BASE = Path(__file__).resolve().parents[1]
LOG_ROOT = BASE.parents[0] / "_logs"
LOG_ROOT.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("SE_EPHE_PATH", str(BASE / "ephe"))
os.environ.setdefault("STYX_GEOCODE_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")
os.environ.setdefault("STYX_GEOIP_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")

cities_path = BASE / "tests" / "fixtures" / "cities.txt"
if cities_path.exists():
    os.environ.setdefault("STYX_CITIES_PATH", str(cities_path))

countries_path = BASE / "tests" / "fixtures" / "countries.txt"
if countries_path.exists():
    os.environ.setdefault("STYX_COUNTRIES_PATH", str(countries_path))

client = TestClient(app)

natal_payload = {
    "metadata": {
        "chart_type": "natal",
        "timestamp_utc": "1982-05-08T06:39:00+03:00",
        "location": "Karadeniz Eregli",
    }
}


def measure(method: str, url: str, **kwargs):
    start = time.perf_counter()
    resp = client.request(method, url, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000.0
    return duration_ms, resp


def write_json(folder: str, name: str, payload: dict):
    out_dir = LOG_ROOT / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


latency = {}

# health
ms, resp = measure("GET", "/v1/health")
latency["health_ms"] = ms
write_json("health", "response.json", resp.json())

# config
ms, resp = measure("GET", "/v1/config")
latency["config_ms"] = ms
write_json("config", "response.json", resp.json())

# chart (natal)
ms, resp = measure("POST", "/v1/chart", json=natal_payload)
latency["chart_natal_ms"] = ms
write_json("chart", "natal.json", resp.json())

# transit basic
transit_payload = {"metadata": {"transit_type": "transit"}, "frame_a": natal_payload}
ms, resp = measure("POST", "/v1/transit", json=transit_payload)
latency["transit_ms"] = ms
write_json("transit", "transit.json", resp.json())

# synastry
syn_payload = {
    "metadata": {"transit_type": "synastry"},
    "frame_a": natal_payload,
    "frame_b": {
        "metadata": {
            "chart_type": "natal",
            "timestamp_utc": "1985-02-12T10:15:00+03:00",
            "location": "Istanbul",
        }
    },
}
ms, resp = measure("POST", "/v1/transit", json=syn_payload)
latency["synastry_ms"] = ms
write_json("transit", "synastry.json", resp.json())

# secondary progression (aspects)
sp_payload = {
    "metadata": {
        "transit_type": "secondary_progression",
        "timestamp_utc": "2026-01-28T10:00:00+03:00",
        "location": "Karadeniz Eregli",
    },
    "frame_a": natal_payload,
}
ms, resp = measure("POST", "/v1/transit", json=sp_payload)
latency["secondary_progression_ms"] = ms
write_json("transit", "secondary_progression.json", resp.json())

# secondary progression chart only
sp_chart_payload = {
    "metadata": {
        "transit_type": "secondary_progression",
        "timestamp_utc": "2026-01-28T10:00:00+03:00",
        "output": "chart",
        "location": "Karadeniz Eregli",
    },
    "frame_a": natal_payload,
}
ms, resp = measure("POST", "/v1/transit", json=sp_chart_payload)
latency["secondary_progression_chart_ms"] = ms
write_json("transit", "secondary_progression_chart.json", resp.json())

# astrocartography
ac_payload = {"metadata": {"transit_type": "astrocartography"}, "frame_a": natal_payload}
ms, resp = measure("POST", "/v1/transit", json=ac_payload)
latency["astrocartography_ms"] = ms
write_json("transit", "astrocartography.json", resp.json())

# lunations list
lun_payload = {
    "metadata": {
        "transit_type": "lunations",
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2026-12-31T23:59:59Z",
    }
}
ms, resp = measure("POST", "/v1/transit", json=lun_payload)
latency["lunations_ms"] = ms
write_json("transit", "lunations.json", resp.json())

# timeline levels
level1_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2031-01-01T00:00:00Z",
        "level": "level1",
    },
    "natal": natal_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level1_payload)
latency["timeline_level1_ms"] = ms
write_json("timeline", "level1.json", resp.json())

level2_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2031-01-01T00:00:00Z",
        "level": "level2",
    },
    "natal": natal_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level2_payload)
latency["timeline_level2_ms"] = ms
write_json("timeline", "level2.json", resp.json())

level3_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2026-12-31T23:59:59Z",
        "level": "eclipses",
    },
    "natal": natal_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level3_payload)
latency["timeline_level3_ms"] = ms
write_json("timeline", "level3_eclipses.json", resp.json())

# progression timeline
prog_payload = {
    "metadata": {
        "start_utc": "1982-05-08T03:39:00Z",
        "end_utc": "1985-05-08T03:39:00Z",
        "step_years": 1,
    },
    "natal": natal_payload,
}
ms, resp = measure("POST", "/v1/progression_timeline", json=prog_payload)
latency["progression_timeline_ms"] = ms
write_json("progression_timeline", "response.json", resp.json())

# write latency
(LOG_ROOT / "latency_all_endpoints.json").write_text(json.dumps(latency, indent=2), encoding="utf-8")
print("Wrote logs and latency")
