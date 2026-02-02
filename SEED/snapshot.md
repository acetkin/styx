ReSpec Snapshot
phase: iteration
active_deliverable: styx-api
snapshot_date: 2026-02-02
snapshot_author: LLM

status_1p: Core endpoints (/v1/health, /v1/config, /v1/chart, /v1/transit, /v1/timeline, /v1/progression_timeline) are implemented with strict request schemas and standardized envelopes; hardening steps 1-4 complete; last pytest run reported passing on 2026-02-02.

key_decisions:
- Envelope response is standard for all endpoints.
- Validation errors return 422 with standardized errors[] and JSON-pointer paths.
- meta.api_version and meta.schema_version are included in every response.
- Astrocartography uses cities/country datasets and returns results plus crossings.
- Lunations/eclipses are served via CSV (no runtime eclipse calculation).

recent_findings:
- Timeline and progression outputs use phases with exact_index for readability.
- Auto/ip location resolves via GeoIP with stub support for offline tests.
- Request logging includes request_id, method, path, status_code, duration_ms.

open_questions:
- Finalize public docs/examples and backward-compatibility policy for S3.
- Confirm whether timeline nodes should remain supported.

blockers:
- None.

next_actions:
- Prepare S3 docs/examples and compatibility policy.
- Re-run pytest and smoke run before public-facing docs freeze.
