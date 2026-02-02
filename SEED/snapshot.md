ReSpec Snapshot
phase: iteration
active_deliverable: styx-api
snapshot_date: 2026-02-02
snapshot_author: LLM

status_1p: Design scope aligned to latest API: endpoints /v1/health, /v1/config, /v1/chart, /v1/transit, /v1/timeline; chart types include natal/moment/solar_arc/secondary_progression; timelines unified for transit/secondary_progression/solar_arc with lunations/eclipses tokens.

key_decisions:
- Unify timelines under /v1/timeline with adaptive scanning.
- Restrict /v1/transit to transit-only; remove on_natal/synastry/astrocartography and progression_timeline endpoint.
- Remove legacy fields (metadata.name, subject, settings.points.lilith, metadata.output/level/body/step_years).

recent_findings:
- Nodes accepted as nn/sn or nodes in timeline bodies.
- Lunations/eclipses exposed via timeline bodies tokens and CSV data.

open_questions:
- Confirm public docs/examples placement for S3 release.
- Confirm if location should remain object-only or if place strings remain supported.

blockers:
- None.

next_actions:
- Update SPIN docs/README examples to match the new API scope.
- Regenerate samples once public docs are finalized.
