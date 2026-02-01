# A_Design

## OVERVIEW (Living)
- intent: Deterministic astrology computation API with envelope responses and reproducible JSON payloads.
- scope: /v1/health, /v1/config, /v1/chart, /v1/transit (transit/on_natal/synastry/astrocartography/solar_arc/secondary_progression + lunations), /v1/timeline (level1/2/3 + lunations/eclipses), /v1/progression_timeline.
- constraints: Python 3.12 target, FastAPI/Uvicorn, Swiss Ephemeris as source of truth, geocoding required or auto/ip, bundled datasets (cities5000, countryInfo, lunations_100y.csv), UTC-normalized inputs, deterministic rounding to 2 decimals.
- success_definition: Same input yields identical output (ordering + rounding); envelope shape stable; tests pass; Swagger examples work.
- key_decisions: Envelope wrapper with data payload; astrocartography returns nearest cities + crossings (no maps); eclipses/lunations served from CSV (no runtime ephemeris calc); fixed-star conjunctions only; lilith mean/true toggle.

## A1 — Features (Living)
- feature_list: /v1/chart (planets, asteroids, angles, houses, nodes, lots, lilith, aspects, fixed-star conjunctions); /v1/config catalogs + defaults + orb tables; /v1/transit modes with cross-aspects, solar arc, secondary progression (aspects or chart), astrocartography (results + crossings), lunations filter; /v1/timeline and /v1/progression_timeline range outputs; geocode/geoip stubs for offline tests.

## A2 — Architecture (Living)
- boundaries: FastAPI service layer; computation core around Swiss Ephemeris; data adapters for geocode/geoip and CSV datasets.
- components: API router, envelope builder, request/response models, ephemeris wrapper, houses/points/aspects calculators, star-conjunction filter, astrocartography engine, timeline/progression engines, lunations CSV loader, geocode resolver.
- data_flows: request -> resolve timestamp/location -> compute chart -> compute aspects/stars/transit/timeline/lunations -> round -> wrap in envelope response.

## A3 — Interaction (Living)
- interaction_rules: ISO-8601 timestamps with offsets accepted; "now" supported where timestamps are optional; location accepts place string, lat/lon object, or "auto/ip" (GeoIP) with optional fallback place; settings defaults to placidus/tropical/ecliptic; lilith defaults to mean; timezone/local timestamp returned when available.
- error_handling: validation errors -> HTTP 422; geocode/geoip failures -> HTTP 422; missing ephemeris data -> HTTP 500; fixed-star calc failures recorded in data.meta.warnings.
