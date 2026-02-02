import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

BASE = Path(__file__).resolve().parents[1]

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


def measure(method: str, url: str, **kwargs):
    start = time.perf_counter()
    resp = client.request(method, url, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000.0
    return duration_ms, resp


results = {}

# /v1/health
ms, resp = measure("GET", "/v1/health")
results["health_ms"] = ms
results["health_status"] = resp.status_code

# /v1/config
ms, resp = measure("GET", "/v1/config")
results["config_ms"] = ms
results["config_status"] = resp.status_code

# /v1/chart
chart_payload = {
    "metadata": {
        "chart_type": "natal",
        "timestamp_utc": "1982-05-08T06:39:00+03:00",
        "location": "Karadeniz Eregli",
    }
}
ms, resp = measure("POST", "/v1/chart", json=chart_payload)
results["chart_ms"] = ms
results["chart_status"] = resp.status_code

# /v1/transit (transit)
transit_payload = {
    "metadata": {"transit_type": "transit"},
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/transit", json=transit_payload)
results["transit_ms"] = ms
results["transit_status"] = resp.status_code

# /v1/transit (synastry)
syn_payload = {
    "metadata": {"transit_type": "synastry"},
    "frame_a": chart_payload,
    "frame_b": {
        "metadata": {
            "chart_type": "natal",
            "timestamp_utc": "1985-02-12T10:15:00+03:00",
            "location": "Istanbul",
        }
    },
}
ms, resp = measure("POST", "/v1/transit", json=syn_payload)
results["synastry_ms"] = ms
results["synastry_status"] = resp.status_code

# /v1/transit (solar_arc)
sa_payload = {
    "metadata": {
        "transit_type": "solar_arc",
        "timestamp_utc": "2026-01-28T10:00:00+03:00",
        "solar_arc_sun": "mean",
    },
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/transit", json=sa_payload)
results["solar_arc_ms"] = ms
results["solar_arc_status"] = resp.status_code

# /v1/transit (secondary_progression)
sp_payload = {
    "metadata": {
        "transit_type": "secondary_progression",
        "timestamp_utc": "2026-01-28T10:00:00+03:00",
        "location": "Karadeniz Eregli",
    },
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/transit", json=sp_payload)
results["secondary_progression_ms"] = ms
results["secondary_progression_status"] = resp.status_code

# /v1/transit (astrocartography)
ac_payload = {
    "metadata": {"transit_type": "astrocartography"},
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/transit", json=ac_payload)
results["astrocartography_ms"] = ms
results["astrocartography_status"] = resp.status_code

# /v1/transit (lunations list)
lun_payload = {
    "metadata": {
        "transit_type": "lunations",
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2026-12-31T23:59:59Z",
    }
}
ms, resp = measure("POST", "/v1/transit", json=lun_payload)
results["lunations_ms"] = ms
results["lunations_status"] = resp.status_code

# /v1/timeline (outer bodies)
level1_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2027-01-01T00:00:00Z",
        "bodies": ["uranus", "neptune", "pluto"],
    },
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level1_payload)
results["timeline_level1_ms"] = ms
results["timeline_level1_status"] = resp.status_code

# /v1/timeline (jupiter/saturn)
level2_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2027-01-01T00:00:00Z",
        "bodies": ["jupiter", "saturn"],
    },
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level2_payload)
results["timeline_level2_ms"] = ms
results["timeline_level2_status"] = resp.status_code

# /v1/timeline (eclipses)
level3_payload = {
    "metadata": {
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2026-12-31T23:59:59Z",
        "bodies": ["eclipses"],
    },
    "frame_a": chart_payload,
}
ms, resp = measure("POST", "/v1/timeline", json=level3_payload)
results["timeline_eclipses_ms"] = ms
results["timeline_eclipses_status"] = resp.status_code

out_path = BASE.parents[0] / "_logs" / "latency_endpoints.json"
out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Wrote {out_path}")
