# A_Design

## OVERVIEW (Living)
- intent: Deterministic astrology computation API with a stable envelope response and reproducible JSON payloads.
- scope: /v1/health, /v1/config, /v1/chart (natal/moment/solar_arc/secondary_progression), /v1/transit (two-frame transit aspects only), /v1/timeline (transit/secondary_progression/solar_arc + lunations/eclipses via bodies list).
- constraints: Python 3.12 target; FastAPI/Uvicorn; Swiss Ephemeris as source of truth; UTC timestamps; location object required; deterministic rounding to 2 decimals for chart/transit outputs; lunations/eclipses sourced from CSV; adaptive timeline scan; legacy fields removed.
- success_definition: Same input yields identical output (ordering + rounding); envelope schema stable; timeline scan consistent; tests pass; examples match runtime behavior.
- key_decisions: Unify timelines under /v1/timeline; restrict /v1/transit to transit only; remove astrocartography/synastry/on_natal/progression_timeline; remove subject/metadata.name/settings.points.lilith and other legacy fields.

## A1 — Features (Living)
- feature_list: /v1/health; /v1/config (defaults, catalogs, orbs, provenance); /v1/chart supports natal/moment/solar_arc/secondary_progression; /v1/transit supports transit aspects between frame_a and frame_b; /v1/timeline supports timeline_type=transit/secondary_progression/solar_arc with bodies list and lunations/eclipses tokens; envelope response on all endpoints.
- timeline_bodies: transit supports uranus/neptune/pluto plus jupiter/saturn and nodes (nn/sn or nodes); solar_arc supports sun..pluto plus nn/sn; lunations/eclipses via bodies tokens: lunations/eclipses/new_moon/full_moon/solar_eclipse/lunar_eclipse.
- timeline_scan: adaptive search (monthly -> weekly -> daily -> hourly -> minute); no step or step_years parameters.

## A2 — Architecture (Living)
- boundaries: FastAPI service layer; computation core around Swiss Ephemeris; dataset adapter for lunations CSV.
- components: API router; envelope builder; request/response models; chart engine; aspect/cross-aspect calculators; timeline engines (transit, solar arc, secondary progression); lunations CSV loader.
- data_flows: request -> validate/normalize -> compute chart/aspects/timeline -> deterministic rounding -> wrap in envelope response.

## A3 — Interaction (Living)
- interaction_rules: ChartFrameRequest uses metadata {chart_type, timestamp_utc, location, client_name?, solar_arc_sun?} and settings {house_system, zodiac, coordinate_system}; location is object {lat, lon, alt_m, place}; no nested frame_a inside ChartFrameRequest.
- transit_rules: /v1/transit requires metadata.transit_type="transit" plus frame_a and frame_b; no other transit_type values.
- timeline_rules: /v1/timeline requires metadata.start_utc/end_utc; timeline_type=transit/secondary_progression/solar_arc; bodies required for transit/solar_arc; "nodes" normalized to nn/sn; lunation/eclipses tokens supported for transit timeline.
- removed_fields: metadata.name, subject, settings.points.lilith, metadata.output, metadata.level/body/step_years, transit_type on_natal/synastry/astrocartography/solar_arc/secondary_progression.
- error_handling: validation errors -> HTTP 422; ephemeris failures -> HTTP 500; errors array non-empty indicates failure.
