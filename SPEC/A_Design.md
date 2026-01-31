# A_Design

## OVERVIEW (Living)
- intent: Deterministic astrology computation core and API returning structured, reproducible JSON data.
- scope: /v1/health, /v1/config, /v1/chart MVP (natal/moment); no interpretive prose.
- constraints: Python 3.12 target, FastAPI/Uvicorn, Swiss Ephemeris as source of truth, geocoding required, UTC-normalized inputs.
- success_definition: Same input yields identical output; MVP payload complete; pytest -q passes; Swagger example works.
- key_decisions: Minimal API surface; deterministic ordering and schemas; geocode required for place strings; fixed-star conjunctions only (default orb 2.0 deg).

## A1 — Features (Living)
- feature_list: /v1/chart (planets Sun..Pluto, asteroids Ceres/Pallas/Juno/Vesta, centaur Chiron, angles, houses, nodes, lots, fixed-star conjunctions); /v1/config catalogs + defaults; /v1/health utility.

## A2 — Architecture (Living)
- boundaries: FastAPI service layer; computation core around Swiss Ephemeris; geocoding adapter.
- components: API router, request/response schemas, ephemeris wrapper, house/points calculators, star-conjunction filter, geocode resolver.
- data_flows: request -> normalize UTC + location -> compute bodies/angles/houses/points/stars -> deterministic ordering -> response.

## A3 — Interaction (Living)
- interaction_rules: ISO-8601 timestamps with offsets accepted; place strings geocoded when lat/lon missing; settings default to placidus/tropical/ecliptic.
- error_handling: geocode failures -> HTTP 422; missing ephemeris files -> warnings in meta; invalid inputs -> validation errors.
