import json
from pathlib import Path

from app.services.astro import calc_chart
from app.services.timeline import build_timeline
from app.models import Settings

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "_logs" / "transit_timeline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

natal_timestamp = "1982-05-08T06:39:00+03:00"
location = {"lat": 41.2795516, "lon": 31.4229672, "alt_m": 0, "place": "Karadeniz Eregli"}
settings = Settings()

natal_chart = calc_chart(
    chart_type="natal",
    timestamp_utc=natal_timestamp,
    location=location,
    settings=settings,
    round_output=False,
)

start_utc = "1982-05-08T03:39:00Z"
end_utc = "2082-05-08T03:39:00Z"

body_sets = {
    "jupiter": ["jupiter"],
    "saturn": ["saturn"],
    "outer": ["uranus", "neptune", "pluto"],
    "nodes": ["nn", "sn"],
}

for label, bodies in body_sets.items():
    payload = build_timeline(
        natal_chart=natal_chart,
        start_utc=start_utc,
        end_utc=end_utc,
        level="custom",
        house_system=settings.house_system,
        bodies=bodies,
    )
    out_path = OUT_DIR / f"timeline_{label}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
