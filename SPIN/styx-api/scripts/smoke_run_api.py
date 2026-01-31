from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _http_json(method: str, url: str, payload: dict | None = None, timeout: float = 10.0) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def _wait_for_health(base_url: str, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    url = f"{base_url}/v1/health"
    while time.time() < deadline:
        try:
            _http_json("GET", url, timeout=3.0)
            return True
        except (HTTPError, URLError, json.JSONDecodeError):
            time.sleep(0.5)
    return False


def _validate_envelope(obj: dict) -> tuple[bool, str]:
    required = {"meta", "settings", "input_summary", "data", "timing", "errors"}
    if set(obj.keys()) != required:
        return False, f"top-level keys mismatch: {sorted(obj.keys())}"
    errors = obj.get("errors")
    if not isinstance(errors, list):
        return False, "errors is not a list"
    if errors:
        return False, f"errors not empty: {errors}"
    return True, "ok"


def main() -> int:
    host = _env_str("SMOKE_HOST", "127.0.0.1")
    port = _env_int("SMOKE_PORT", 8000)
    timeout_s = _env_float("SMOKE_TIMEOUT", 30.0)
    base_url = f"http://{host}:{port}"

    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "SPIN" / "_logs" / "samples" / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "uvicorn.log"

    api_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(api_root)

    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
            cwd=api_root,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    try:
        if not _wait_for_health(base_url, timeout_s):
            print("Health check failed: timeout waiting for /v1/health")
            return 1

        base_location = {"lat": 40.7128, "lon": -74.0060, "alt_m": 10, "place": "NYC"}
        chart_req = {
            "metadata": {
                "chart_type": "natal",
                "timestamp_utc": "2024-01-01T00:00:00Z",
                "location": base_location,
                "name": "Test",
            },
            "settings": {
                "house_system": "placidus",
                "zodiac": "tropical",
                "coordinate_system": "ecliptic",
                "points": {"lilith": "mean"},
            },
        }

        transit_req = {
            "metadata": {
                "transit_type": "transit",
                "timestamp_utc": "2024-01-02T00:00:00Z",
                "location": base_location,
            },
            "frame_a": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "2000-01-01T00:00:00Z",
                    "location": base_location,
                },
                "settings": {
                    "house_system": "placidus",
                    "zodiac": "tropical",
                    "coordinate_system": "ecliptic",
                },
            },
            "frame_b": {
                "metadata": {
                    "chart_type": "moment",
                    "timestamp_utc": "2024-01-02T00:00:00Z",
                    "location": base_location,
                },
                "settings": {
                    "house_system": "placidus",
                    "zodiac": "tropical",
                    "coordinate_system": "ecliptic",
                },
            },
        }

        timeline_req = {
            "metadata": {
                "start_utc": "2024-01-01T00:00:00Z",
                "end_utc": "2024-02-01T00:00:00Z",
                "level": "level1",
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "2000-01-01T00:00:00Z",
                    "location": base_location,
                },
                "settings": {
                    "house_system": "placidus",
                    "zodiac": "tropical",
                    "coordinate_system": "ecliptic",
                },
            },
        }

        progression_req = {
            "metadata": {
                "start_utc": "2024-01-01T00:00:00Z",
                "end_utc": "2024-02-01T00:00:00Z",
                "step_years": 1,
            },
            "natal": {
                "metadata": {
                    "chart_type": "natal",
                    "timestamp_utc": "2000-01-01T00:00:00Z",
                    "location": base_location,
                },
                "settings": {
                    "house_system": "placidus",
                    "zodiac": "tropical",
                    "coordinate_system": "ecliptic",
                },
            },
        }

        requests = [
            ("health", "GET", "/v1/health", None),
            ("config", "GET", "/v1/config", None),
            ("chart", "POST", "/v1/chart", chart_req),
            ("transit", "POST", "/v1/transit", transit_req),
            ("timeline", "POST", "/v1/timeline", timeline_req),
            ("progression_timeline", "POST", "/v1/progression_timeline", progression_req),
        ]

        failures: list[str] = []
        for name, method, path, payload in requests:
            url = f"{base_url}{path}"
            try:
                response = _http_json(method, url, payload=payload, timeout=30.0)
            except (HTTPError, URLError, json.JSONDecodeError) as exc:
                failures.append(f"{name}: request failed: {exc}")
                continue

            out_path = output_dir / f"{name}.json"
            out_path.write_text(json.dumps(response, indent=2, ensure_ascii=True), encoding="utf-8")

            ok, reason = _validate_envelope(response)
            if not ok:
                failures.append(f"{name}: {reason}")

        if failures:
            print("Smoke run failed:")
            for item in failures:
                print(f"- {item}")
            return 1

        print(f"Smoke run OK. Output: {output_dir}")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())

