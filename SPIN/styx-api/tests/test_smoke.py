from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _client(monkeypatch: object) -> TestClient:
    ephe_path = Path(__file__).resolve().parents[1] / "ephe"
    if ephe_path.exists():
        monkeypatch.setenv("SE_EPHE_PATH", str(ephe_path))
    monkeypatch.setenv("STYX_GEOCODE_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")
    monkeypatch.setenv("STYX_GEOIP_STUB", "41.2795516,31.4229672,0,Karadeniz Eregli")
    return TestClient(app)


def _assert_meta(resp: object) -> None:
    meta = resp.json().get("meta") or {}
    assert meta.get("request_id")
    assert meta.get("api_version")
    assert meta.get("schema_version")


def test_smoke_success(monkeypatch: object) -> None:
    client = _client(monkeypatch)

    resp = client.get("/v1/health")
    assert resp.status_code == 200
    _assert_meta(resp)
    assert resp.json().get("errors") == []
    first_request_id = resp.json()["meta"]["request_id"]

    resp = client.get("/v1/health")
    assert resp.status_code == 200
    second_request_id = resp.json()["meta"]["request_id"]
    assert first_request_id != second_request_id

    resp = client.get("/v1/config")
    assert resp.status_code == 200
    _assert_meta(resp)
    assert resp.json().get("errors") == []

    resp = client.post(
        "/v1/chart",
        json={
            "metadata": {
                "chart_type": "natal",
                "timestamp_utc": "1982-05-08T06:39:00+03:00",
                "location": "Karadeniz Eregli",
            }
        },
    )
    assert resp.status_code == 200
    _assert_meta(resp)
    assert resp.json().get("errors") == []


def test_smoke_unknown_field(monkeypatch: object) -> None:
    client = _client(monkeypatch)
    resp = client.post(
        "/v1/chart",
        json={
            "metadata": {
                "chart_type": "natal",
                "timestamp_utc": "1982-05-08T06:39:00+03:00",
                "location": "Karadeniz Eregli",
                "name": "Legacy Name",
            }
        },
    )
    assert resp.status_code == 422
    _assert_meta(resp)
    errors = resp.json().get("errors") or []
    assert errors
    assert errors[0].get("path") == "/metadata/name"
    assert errors[0].get("code") in {"UNKNOWN_FIELD", "VALIDATION_ERROR"}
