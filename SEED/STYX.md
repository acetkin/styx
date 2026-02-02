# Seed
## Project Identity
name: STYX
output_family: Code

## One-Sentence Description
Deterministic astrology computation core and API that returns structured, reproducible data without interpretive prose.

## Goals
- Provide stable envelope responses with deterministic chart/transit/timeline outputs and full provenance.
- Keep the API surface minimal while supporting core modes via /v1/transit and range outputs via /v1/timeline and /v1/progression_timeline.
- Ship data-only astrocartography and lunations/eclipses workflows without rendering.
- Maintain runnable tests and smoke-run samples for validation.

## Non-Goals
- Generating interpretive prose or horoscope text.
- Rendering maps or visuals (astrocartography is data-only).
- Computing eclipses in the API runtime (use lunations CSV).
- Persisting user data or profiles.

## Deliverables
- GET /v1/health (envelope).
- GET /v1/config with defaults, catalogs, orbs, and provenance.
- POST /v1/chart with planets Sun..Pluto, asteroids Ceres/Pallas/Juno/Vesta/Chiron, angles/houses, nodes, lots, lilith, aspects, fixed-star conjunctions.
- POST /v1/transit modes: transit, on_natal, synastry, solar_arc (mean/true sun), secondary_progression (aspects or chart), astrocartography (results + crossings), lunations filter.
- POST /v1/timeline for level1/level2 (transit events) and level3/lunations/eclipses (CSV-backed events).
- POST /v1/progression_timeline for range-based progression events (outer planets excluded).
- Data files under SPIN/styx-api/data: cities5000.txt, countryInfo.txt, lunations_100y.csv.
- Tests: pytest -q; smoke-run script writes samples to SPIN/_logs.

## Constraints
- Runtime: Python 3.12 target, FastAPI, Uvicorn.
- Swiss Ephemeris is the single source of astronomical truth; path via SE_EPHE_PATH.
- Geocoding required for place strings; supports GeoIP via "auto/ip" and stubs for tests.
- Inputs normalized to UTC internally; timestamp accepts ISO-8601 with offset.
- Deterministic ordering and rounding to 2 decimals for chart/transit payloads.
- Bundled datasets for astrocartography and lunations are required.

## Acceptance Criteria
- Same request yields identical response (ordering + rounding) across runs.
- All endpoints return the envelope shape with stable schema fields.
- /v1/config catalogs match implemented lists and default settings.
- /v1/transit returns aspects for relationship modes and data-only outputs for astrocartography/lunations.
- /v1/timeline and /v1/progression_timeline return events with phases across a requested range.
- pytest -q passes locally; smoke run produces envelope-valid samples.

## API Surface (Accepted Decisions)
- endpoints:
  - GET /v1/health
  - GET /v1/config
  - POST /v1/chart
  - POST /v1/transit
  - POST /v1/timeline
  - POST /v1/progression_timeline
- request model (chart/transit):
  - body: { metadata, subject?, settings? }
  - metadata.timestamp_utc: ISO-8601; may include offset; "now" supported where optional
  - metadata.location: string place | object {lat, lon, alt_m?, place?} | "auto"/"ip" (GeoIP)
  - settings defaults: house_system=placidus, zodiac=tropical, coordinate_system=ecliptic
  - settings.points.lilith: mean | true (mean default)
- request model (timeline/progression):
  - start_utc/end_utc required; level selects bodies or lunations
  - progression_timeline supports step_years

## Response Contents (v1 Catalog)
Top-level envelope: { meta, settings, input_summary, data, timing, errors }

- meta:
  - schema_version, engine_version
  - request_id, created_at_utc
  - ephemeris { provider, version?, flags? }
- settings: resolved zodiac/house_system/coordinates/orbs
- input_summary: datetime_local/timezone/datetime_utc/location
- data: payload specific to endpoint
- timing: latency_ms, compute_ms, cache?
- errors: [] on success

Chart data payload (data):
- meta: output_type, mode, chart_type, timestamp_utc, timestamp_local?, timezone?, location, warnings?
- bodies: planets Sun..Pluto
- asteroids: Ceres/Pallas/Juno/Vesta/Chiron + Lilith asteroid entries
- angles: asc/dsc/mc/ic
- houses: system + cusps
- points: nn/sn, lots, lilith (black moon)
- aspects: list of {a,b,type,exact_angle,orb,applying,separating}
- stars: conjunctions with fixed stars

Transit data payload (data):
- meta: transit_type, timestamp_utc, optional solar_arc_sun
- aspects: cross-aspects between frames for relationship modes
- results/crossings for astrocartography
- events for lunations filter

Timeline data payload (data):
- meta: start_utc, end_utc, level
- events: transit/natal/aspect with phases (approaching/exact/separating)

Progression timeline data payload (data):
- meta: start_utc, end_utc, step_years
- events: progression aspects with phases, outer planets excluded

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

### Response (envelope + chart excerpt)
```json
{
  "meta": { "schema_version": "1.0", "engine_version": "0.1.0", "request_id": "...", "created_at_utc": "..." },
  "settings": { "house_system": "placidus", "zodiac": { "type": "tropical" } },
  "input_summary": { "datetime_utc": "1982-05-08T03:39:00Z" },
  "data": {
    "meta": { "output_type": "natal", "mode": "chart", "chart_type": "natal", "timestamp_utc": "1982-05-08T03:39:00Z" },
    "bodies": { "sun": { "lon": 0.0, "lat": 0.0, "speed": 0.0, "retrograde": false, "sign": "Aries", "deg_in_sign": 0.0, "house": 1 } },
    "angles": { "asc": { "lon": 0.0, "sign": "Aries", "deg_in_sign": 0.0 } },
    "houses": { "system": "placidus", "cusps": { "1": { "lon": 0.0, "sign": "Aries", "deg_in_sign": 0.0 } } },
    "points": { "nn": { "lon": 0.0, "lat": 0.0 } },
    "aspects": [],
    "stars": []
  },
  "timing": { "latency_ms": 0.0, "compute_ms": 0.0, "cache": { "hit": false } },
  "errors": []
}
```

## Operational Rules (Accepted)
- Determinism: same input -> same output, including ordering and rounding.
- Geocoding is always on; "auto/ip" uses GeoIP; failures return HTTP 422.
- Missing ephemeris data or path returns HTTP 500.
- Fixed-star calc failures are recorded in data.meta.warnings when applicable.

## Stage & Plan Context (Accepted)
- Stage: S3 (Release / Stable); Next: NONE.
- Near-term focus:
  - Finalize public docs and examples.
  - Lock backward-compatibility policy and versioning.

## Suggested SPIN Output
deliverable_folder_name: styx-api



## C Output Types and Timelines (from SPEC/Develop/B_Develop.md)

### 1 Direct Output Types
- Direct outputs: /v1/chart (natal/moment), /v1/transit (transit/on_natal/synastry/solar_arc/secondary_progression/astrocartography), all wrapped in the envelope.
- Astrocartography is data-only: nearest cities/places per line with crossings (no rendered maps).

### 2 Calculated Output Types
- /v1/timeline: level1 (outer planets), level2 (Saturn + Jupiter), level3/lunations/eclipses from lunations CSV.
- /v1/progression_timeline: range-based progression events with phases and exact_index; outer planets excluded.

### 3 Output JSON Formats
- Envelope always wraps the data payload; examples in Canonical JSON Examples above.
