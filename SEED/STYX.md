# Seed
## Project Identity
name: STYX
output_family: Code

## One-Sentence Description
Deterministic astrology computation core and API that returns structured, reproducible data without interpretive prose.

## Goals
- Provide a stable, LLM-friendly JSON schema for natal/moment charts with deterministic outputs and full provenance.
- Keep the API surface minimal (two computational endpoints) with backward-safe expansion via modes.
- Ship a working MVP for /v1/chart with planets, minimal asteroids, Chiron, houses, nodes, lots, and fixed-star conjunctions.

## Non-Goals
- Generating interpretive prose or horoscope text.
- Expanding routes beyond the two computational endpoints in v1.
- Rendering maps or visuals (astrocartography is data-only, later under /v1/transit).

## Deliverables
- POST /v1/chart MVP with:
  - planets: Sun..Pluto
  - asteroids: Ceres, Pallas, Juno, Vesta (in `asteroids`)
  -   - angles + houses (labeled cusps {1..12})
  - points: True Node (nn/sn) + lots {fortune, spirit, necessity, love, courage, victory, nemesis}
  - fixed stars: conjunction-only list (default orb 2.0 deg)
- GET /v1/config exposing catalogs and defaults.
- Basic tests (pytest + httpx) passing; Swagger examples runnable.

## Constraints
- Runtime: Python (target 3.12; dev verified on 3.11), FastAPI, Uvicorn.
- Swiss Ephemeris is the single source of astronomical truth; path via env `SE_EPHE_PATH`.
- Geocoding is required for place strings; uses Nominatim via geopy (or `STYX_GEOCODE_STUB` for tests/offline).
- All inputs normalized to UTC internally; timestamp supports local offset (ISO-8601) and is echoed.

## Acceptance Criteria
- Same request yields identical response (fields/values) across runs.
- /v1/chart returns the MVP payload above; houses assigned for all returned bodies.
- /v1/config catalogs: `asteroids=[ceres,pallas,juno,vesta,chiron]`.
- Tests: `pytest -q` passes locally; Swagger `/docs` loads and example call works.

## API Surface (Accepted Decisions)
- endpoints:
  - GET /v1/health (utility)
  - GET /v1/config (defaults + catalogs)
  - POST /v1/chart (natal or moment via `metadata.chart_type`)
- request model:
  - body: `{ metadata, subject?, settings? }`
  - `metadata.timestamp_utc`: ISO-8601; supports offset (e.g., `1982-05-08T06:39:00+03:00`).
  - `metadata.location`: string place or object `{lat, lon, alt_m?, place?}`.
  - geocoding: required; if place string and lat/lon missing, server geocodes; failure -> HTTP 422.
- settings defaults:
  - `house_system=placidus`, `zodiac=tropical`, `coordinate_system=ecliptic`.
- catalogs:\n  - asteroids (default v1 set): `[ceres, pallas, juno, vesta, chiron]`.
  -   - fixed stars: internal default name list; conjunction-only policy; star orb default 2.0 deg (configurable later).

## Response Contents (v1 Catalog)
Top-level shape: { meta, bodies, asteroids, angles, houses, points, aspects, stars }

- meta (required keys and types)
  - `output_type: string` — equals `chart_type` (`natal | moment`)
  - `mode: string` — `"chart"`
  - `chart_type: string` — `natal | moment`
  - `timestamp_utc: string` — ISO-8601; may include offset, echoed as provided
  - `location: { lat:number, lon:number, alt_m:number, place:string? }` — effective
  - `settings: { house_system:string, zodiac:string, coordinate_system:string }` — effective
  - `provenance: { swisseph_version:string, flags:{ topocentric:boolean } }`
  - `star_orb: number` — degrees; default `2.0`
  - `warnings: string[]` — non-fatal issues (e.g., missing ephemeris files)

- bodies (planets, always included)
  - ids: `[sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto]`
  - each: `{ lon, lat, speed, retrograde, sign, deg_in_sign, house }`

- asteroids (default): ids `[ceres, pallas, juno, vesta, chiron]` — each `{ lon, lat, speed, retrograde, sign, deg_in_sign, house }`\n  - ephemeris files required for classical 4: `se00001s.se1, se00002s.se1, se00003s.se1, se00004s.se1`; Chiron uses built-in SwissEphem id

- angles
  - keys: `{ asc, dsc, mc, ic }` (degrees)

- houses
  - object: `{ system:"placidus", cusps:{ 1:number, ..., 12:number } }` (degrees, 1..12)
  - rule: houses are assigned for planets, asteroids, and centaurs

- points
  - nodes: `nn` (True Node), `sn` (computed as opposite of nn)
  - lots (day/night formulas)
    - day: `fortune=Asc+Moon-Sun`, `spirit=Asc+Sun-Moon`, `necessity=Asc+Saturn-Fortune`, `love=Asc+Venus-Spirit`, `courage=Asc+Mars-Fortune`, `victory=Asc+Jupiter-Spirit`, `nemesis=Asc+Saturn-Sun`
    - night: `fortune=Asc+Sun-Moon`, `spirit=Asc+Moon-Sun`, `necessity=Asc+Fortune-Saturn`, `love=Asc+Spirit-Venus`, `courage=Asc+Fortune-Mars`, `victory=Asc+Spirit-Jupiter`, `nemesis=Asc+Sun-Saturn`
  - planned: `points.lilith` (mean/true toggle) in S2

- aspects (planned in S2; listed here for policy lock)
  - supported angles: `{ 0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180 }`
  - default set: `major` = `{ 0, 60, 90, 120, 180 }`, `major_minor` = full set above
  - default orbs: `major = 6..8 deg`, `minor = 1..3 deg` (exact table to be echoed in `meta` when enabled)
  - record shape: `{ a, b, type, exact_angle, orb, applying, separating, exactness_score? }`

- stars (fixed-star conjunctions)
  - policy: conjunction-only within `star_orb` (default 2.0 deg)
  - targets (intended): `planets + asteroids + centaurs` (implemented), `+ angles + nodes + lots` (planned)
  - record: `{ star, target, orb, star_lon, star_lat, target_lon }`

## Canonical JSON Examples
### Request (place string + offset)
```json
{
  "metadata": {
    "chart_type": "natal",
    "timestamp_utc": "1982-05-08T06:39:00+03:00",
    "location": "Karadeniz Eregli"
  },
  "settings": {
    "house_system": "placidus",
    "zodiac": "tropical",
    "coordinate_system": "ecliptic"
  }
}
```

### Minimal Response (schema excerpt)
```json
{
  "meta": {
    "output_type": "natal",
    "mode": "chart",
    "chart_type": "natal",
    "timestamp_utc": "1982-05-08T06:39:00+03:00",
    "location": { "lat": 41.2795516, "lon": 31.4229672, "alt_m": 0, "place": "Karadeniz Eregli" },
    "settings": { "house_system": "placidus", "zodiac": "tropical", "coordinate_system": "ecliptic" },
    "provenance": { "swisseph_version": "...", "flags": { "topocentric": false } },
    "star_orb": 2.0,
    "warnings": []
  },
  "bodies": { "sun": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "Aries", "deg_in_sign": 0.0, "house": 1 } },
  "asteroids": { "ceres": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "Aries", "deg_in_sign": 0.0, "house": 1 } },
  "centaurs": { "chiron": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "Aries", "deg_in_sign": 0.0, "house": 1 } },
  "angles": { "asc": 0.0, "dsc": 180.0, "mc": 90.0, "ic": 270.0 },
  "houses": { "system": "placidus", "cusps": { "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0 } },
  "points": {
    "nn": { "lon": 0.0, "lat": 0.0 },
    "sn": { "lon": 180.0, "lat": 0.0 },
    "lots": { "fortune": { "lon": 0.0 }, "spirit": { "lon": 0.0 }, "necessity": { "lon": 0.0 }, "love": { "lon": 0.0 }, "courage": { "lon": 0.0 }, "victory": { "lon": 0.0 }, "nemesis": { "lon": 0.0 } }
  },
  "aspects": [],
  "stars": []
}
```

## Operational Rules (Accepted)
- Determinism: same input -> same output, including ordering and numeric fields.
- Geocoding is always on; failure to resolve place -> HTTP 422. `STYX_GEOCODE_STUB` may be used for offline testing.
- Missing ephemeris files produce safe fallbacks per-body and a `meta.warnings` entry.
- Houses are computed for planets, asteroids, and centaurs.

## Stage & Plan Context (Accepted)
- Stage: S1 (MVP / First Working Slice); Next: S2 (Hardening/Aspects/Timelines/Eclipses)
- Near-term tasks:
  - Add aspects (major set) with explicit orb table in `meta`.
  - Add points.lilith (mean/true toggle) under `settings.points.lilith`.
  - Add /v1/transit skeleton and first mode.

## Suggested SPIN Output
deliverable_folder_name: styx-api



## C Output Types and Timelines (from SPEC/DEVELOP/B_Develop.md)

### 1 Direct Output Types
- Direct outputs are `{ natal, moment }` via `/v1/chart` (with natal aspects + catalogs always included), and `{ transit, synastry, astrocartography, solar_arc, secondary_progression }` via `/v1/transit` modes selected by `metadata.transit_type`, while preserving one output family.
- Astrocartography is returned as "nearest cities/places per line" (ASC/DSC/MC/IC per body) rather than a rendered map, typically as ranked results `{ body, angle_line, city, country, lat, lon, distance_km, confidence? }` to keep outputs API-native and lightweight.
- Output JSON formats are consistent across modes by design: shared keys (`meta`, `bodies`, `angles`, `houses`, `points`) remain stable, and optional sections (`aspects`, `events`, `eclipses`, `results`) appear predictably when the selected mode requires them.

### 2 Calculated Output Types
- Calculated outputs include `timeline_major` (major transits timeline), `secondary_progression_100y` (a 0–100 year secondary progression timeline from birth), `eclipses` (eclipse list), and `eclipse_transits` (transits at solar/lunar eclipse moments), returned as `events[]`, `eclipses[]`, and/or time-stamped sampled frames depending on the selected mode.
- The "powerful" timeline focuses by default on `{ Saturn, Uranus, Neptune, Pluto }` contacting natal planets, asteroids, angles, and nodes, using the default aspect subset `{ 0, 60, 120, 180 }` while remaining configurable.
- Eclipse computation is global over a requested horizon (e.g., 100 years from birth) and can return both a plain eclipse list (`eclipses[]`) and paired transit snapshots (`eclipse_transits`) so the same engine supports long-term planning and short-term narratives.

### 3 Output JSON Formats

- Chart family JSON (outputs: `natal`, `moment`)
```json
{
  "meta": {
    "output_type": "natal",
    "mode": "chart",
    "chart_type": "natal",
    "timestamp_utc": "1982-05-08T03:39:00Z",
    "location": { "lat": 41.2894444, "lon": 31.4180556, "alt_m": 0, "place": "Karadeniz Eregli, Zonguldak, TR" },
    "settings": { "house_system": "placidus", "zodiac": "tropical", "coordinate_system": "ecliptic" },
    "provenance": { "swisseph_version": "...", "flags": { "topocentric": false } }
  },
  "bodies": {
    "sun": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "Taurus", "deg_in_sign": 0.0, "house": 1 },
    "moon": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "...", "deg_in_sign": 0.0, "house": 1 }
  },
  "angles": { "asc": 0.0, "dsc": 180.0, "mc": 90.0, "ic": 270.0 },
  "houses": { "system": "placidus", "cusps": [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0] },
  "points": {
    "nn": { "lon": 0.0, "lat": 0.0 },
    "sn": { "lon": 180.0, "lat": 0.0 },
    "lots": { "fortune": { "lon": 0.0 }, "spirit": { "lon": 0.0 }, "necessity": { "lon": 0.0 }, "love": { "lon": 0.0 }, "courage": { "lon": 0.0 }, "victory": { "lon": 0.0 }, "nemesis": { "lon": 0.0 } }
  }
}
```

- Relationship family JSON (outputs: `transit`, `synastry`)
```json
{
  "meta": {
    "output_type": "transit",
    "mode": "transit",
    "transit_type": "on_natal",
    "timestamp_utc": "2025-12-17T07:00:00Z",
    "settings": { "aspects": { "set": "major", "orbs": { "major": [6,8], "minor": [1,3] } } }
  },
  "frame_a": { "label": "natal", "chart": { "bodies": {}, "angles": {}, "houses": {}, "points": {} } },
  "frame_b": { "label": "moment", "chart": { "bodies": {}, "angles": {}, "houses": {}, "points": {} } },
  "aspects": [ { "a": "tr_saturn", "b": "natal_sun", "type": 90, "exact_angle": 90, "orb": 1.2, "applying": true, "separating": false } ]
}
```

- Timeline and special-mode JSON (outputs: `timeline_major`, `secondary_progression`, `secondary_progression_100y`, `eclipses`, `eclipse_transits`, `astrocartography`, `solar_arc`)
```json
{
  "meta": { "output_type": "timeline_major", "mode": "timeline", "transit_type": "timeline_major", "horizon": { "years": 100 } },
  "events": [ { "start_utc": "2026-01-01T00:00:00Z", "peak_utc": "2026-02-14T12:00:00Z", "end_utc": "2026-03-10T00:00:00Z", "a": "tr_pluto", "b": "natal_mars", "aspect": 120, "orb_at_peak": 0.1, "phase": "exact" } ]
}
```

```json
{
  "meta": { "output_type": "eclipses", "mode": "eclipses", "transit_type": "eclipses", "horizon": { "years": 100 } },
  "eclipses": [ { "kind": "solar", "timestamp_utc": "2030-06-01T00:00:00Z", "type": "total", "magnitude": 1.0 } ]
}
```

```json
{
  "meta": { "output_type": "eclipse_transits", "mode": "eclipses", "transit_type": "eclipse_transits" },
  "eclipses": [ { "kind": "lunar", "timestamp_utc": "2031-01-01T00:00:00Z" } ],
  "events": [ { "peak_utc": "2031-01-01T00:00:00Z", "a": "eclipse", "b": "natal_moon", "aspect": 0, "orb_at_peak": 0.0, "phase": "exact" } ]
}
```

```json
{
  "meta": { "output_type": "astrocartography", "mode": "astrocartography", "transit_type": "astrocartography" },
  "results": [ { "body": "venus", "angle_line": "mc", "city": "Lisbon", "country": "PT", "lat": 38.72, "lon": -9.14, "distance_km": 42.0 } ]
}
```
