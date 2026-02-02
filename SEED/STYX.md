# Seed
## Project Identity
name: STYX
output_family: Code

## One-Sentence Description
Deterministic astrology computation API built on Swiss Ephemeris with stable envelope responses and unified timelines.

## Goals
- Provide stable envelope responses with deterministic chart/transit/timeline outputs.
- Support single-chart generation (natal, moment, solar_arc, secondary_progression) and two-frame transit aspects.
- Provide unified /v1/timeline for transit, secondary_progression, and solar_arc with adaptive scanning and lunations/eclipses tokens.
- Maintain runnable tests and smoke-run samples for validation.

## Non-Goals
- Generating interpretive prose or horoscope text.
- Rendering maps or visuals (no astrocartography).
- Relationship modes beyond transit (no on_natal or synastry).
- Separate progression_timeline endpoint.
- Computing eclipses at runtime beyond the CSV dataset.

## Deliverables
- GET /v1/health (envelope).
- GET /v1/config with defaults, catalogs, orbs, and provenance.
- POST /v1/chart with chart_type: natal, moment, solar_arc, secondary_progression.
- POST /v1/transit with transit_type: transit (two-frame cross-aspects).
- POST /v1/timeline with timeline_type: transit, secondary_progression, solar_arc; bodies list and lunations/eclipses tokens.
- Data files under SPIN/styx-api/data: lunations_100y.csv.
- Tests: pytest -q; smoke-run script writes samples to SPIN/_logs.

## Constraints
- Runtime: Python 3.12 target, FastAPI, Uvicorn.
- Swiss Ephemeris is the single source of astronomical truth; path via SE_EPHE_PATH.
- Inputs normalized to UTC internally; timestamp accepts ISO-8601.
- Location is an object {lat, lon, alt_m, place} where required.
- Deterministic ordering and rounding to 2 decimals for chart/transit payloads.
- Legacy fields are removed (metadata.name, subject, settings.points.lilith, metadata.output/level/body/step_years, transit_type on_natal/synastry/astrocartography/solar_arc/secondary_progression).

## Acceptance Criteria
- Same request yields identical response (ordering + rounding) across runs.
- All endpoints return the envelope shape with stable schema fields.
- /v1/transit returns cross-aspects for transit only.
- /v1/timeline supports transit/secondary_progression/solar_arc with adaptive scanning and lunations/eclipses tokens.
- pytest -q passes locally; smoke run produces envelope-valid samples.

## API Surface (Accepted Decisions)
- endpoints:
  - GET /v1/health
  - GET /v1/config
  - POST /v1/chart
  - POST /v1/transit
  - POST /v1/timeline
- chart request:
  - metadata.chart_type: natal | moment | solar_arc | secondary_progression
  - metadata.timestamp_utc: ISO-8601
  - metadata.location: {lat, lon, alt_m?, place?}
  - metadata.client_name: optional label
  - metadata.solar_arc_sun: mean | true (only for solar_arc)
  - settings: {house_system, zodiac, coordinate_system}
- transit request:
  - metadata.transit_type: transit
  - metadata.timestamp_utc: ISO-8601
  - metadata.location: {lat, lon, alt_m?, place?}
  - frame_a: ChartFrameRequest (natal or moment)
  - frame_b: ChartFrameRequest (natal or moment)
- timeline request:
  - metadata.start_utc / end_utc: required
  - metadata.timeline_type: transit | secondary_progression | solar_arc
  - metadata.bodies: required for transit/solar_arc
  - bodies allowed: uranus, neptune, pluto, jupiter, saturn, nn, sn, nodes
  - lunations/eclipses tokens (transit timeline): lunations, eclipses, new_moon, full_moon, solar_eclipse, lunar_eclipse

## Response Contents (v1 Catalog)
Top-level envelope: { meta, settings, input_summary, data, timing, errors }

Chart data payload (data):
- meta: output_type, mode, chart_type, timestamp_utc, location, client_name?
- bodies, asteroids, angles, houses, points, aspects, stars (deterministic ordering)

Transit data payload (data):
- meta: transit_type, timestamp_utc
- aspects: cross-aspects between frame_a and frame_b

Timeline data payload (data):
- meta: start_utc, end_utc, timeline_type, bodies
- events: transit/natal/aspect with phases (approaching/exact/separating)

## Canonical JSON Examples
### Chart (natal)
```json
{
  "metadata": {
    "chart_type": "natal",
    "timestamp_utc": "1982-05-08T06:39:00Z",
    "location": { "lat": 41.2796, "lon": 31.4230, "alt_m": 0, "place": "Karadeniz Eregli" },
    "client_name": "Client A"
  },
  "settings": {
    "house_system": "placidus",
    "zodiac": "tropical",
    "coordinate_system": "ecliptic"
  }
}
```

### Transit (two-frame)
```json
{
  "metadata": {
    "transit_type": "transit",
    "timestamp_utc": "2024-03-10T08:15:00Z",
    "location": { "lat": 41.01, "lon": 28.97, "alt_m": 5, "place": "Istanbul" }
  },
  "frame_a": {
    "metadata": {
      "chart_type": "natal",
      "timestamp_utc": "1990-01-01T12:00:00Z",
      "location": { "lat": 41.01, "lon": 28.97, "alt_m": 5, "place": "Istanbul" },
      "client_name": "Client A"
    },
    "settings": {
      "house_system": "placidus",
      "zodiac": "tropical",
      "coordinate_system": "ecliptic"
    }
  },
  "frame_b": {
    "metadata": {
      "chart_type": "moment",
      "timestamp_utc": "2024-03-10T08:15:00Z",
      "location": { "lat": 41.01, "lon": 28.97, "alt_m": 5, "place": "Istanbul" },
      "client_name": "Client A"
    },
    "settings": {
      "house_system": "placidus",
      "zodiac": "tropical",
      "coordinate_system": "ecliptic"
    }
  }
}
```

### Timeline (solar_arc)
```json
{
  "metadata": {
    "start_utc": "2024-01-01T00:00:00Z",
    "end_utc": "2026-01-01T00:00:00Z",
    "timeline_type": "solar_arc",
    "bodies": ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "nn", "sn"]
  },
  "frame_a": {
    "metadata": {
      "chart_type": "natal",
      "timestamp_utc": "1990-01-01T12:00:00Z",
      "location": { "lat": 41.01, "lon": 28.97, "alt_m": 5, "place": "Istanbul" },
      "client_name": "Client A"
    },
    "settings": {
      "house_system": "placidus",
      "zodiac": "tropical",
      "coordinate_system": "ecliptic"
    }
  }
}
```

## Operational Rules (Accepted)
- Determinism: same input -> same output, including ordering and rounding.
- Legacy fields are rejected; only current request shapes are accepted.
- Missing ephemeris data or path returns HTTP 500.

## Stage & Plan Context (Accepted)
- Stage: S3 (Release / Stable); Next: NONE.
- Near-term focus:
  - Finalize public docs and examples.
  - Lock backward-compatibility policy and versioning.

## Suggested SPIN Output
deliverable_folder_name: styx-api

## C Output Types and Timelines (from SPEC/Develop/B_Develop.md)

### 1 Direct Output Types
- /v1/chart (natal/moment/solar_arc/secondary_progression), /v1/transit (transit only), all wrapped in the envelope.

### 2 Calculated Output Types
- /v1/timeline: transit, secondary_progression, solar_arc.
- Lunations/eclipses exposed via bodies tokens in transit timeline.

### 3 Output JSON Formats
- Envelope always wraps the data payload; examples in Canonical JSON Examples above.
