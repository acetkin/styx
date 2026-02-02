# B_Develop

## OVERVIEW (Living)
- implementation_strategy: Build FastAPI service with Swiss Ephemeris wrappers, envelope responses, and unified timeline engines under SPIN/styx-api.
- quality_bar: Deterministic outputs (ordering + rounding); envelope shape stable; timelines scanned adaptively; tests pass; Swagger examples load.
- packaging_policy: Submission-ready code + data only in SPIN/styx-api; non-submission artifacts in SPIN/_local and SPIN/_logs.
- test_policy: pytest -q (httpx) plus optional scripts/smoke_run_api.py.

## STAGES (Living)
- current_stage: S3
- next_stage: NONE
- active_deliverable: styx-api

### S0 — Setup / Alignment
- goal: Normalize SEED, create SPEC skeleton, and capture snapshot.
- exit_criteria:
  - SEED/reSpec.md and SEED/STYX.md present
  - SPEC/A_Design.md, SPEC/B_Develop.md, SPEC/C_Distribute.md created
  - SEED/snapshot.md created
  - SPIN workspace created

### S1 — MVP / First Working Slice
- goal: Implement /v1/chart (natal/moment) and /v1/config with deterministic outputs; include aspects.
- exit_criteria:
  - /v1/chart returns full MVP payload
  - /v1/config catalogs include defaults
  - Aspects enabled with explicit orb table
  - pytest -q passes

### S2 — Hardening / Feedback Loop
- goal: Add solar_arc/secondary_progression charts, /v1/transit (transit only), and /v1/timeline (transit/secondary_progression/solar_arc + lunations/eclipses).
- exit_criteria:
  - /v1/chart supports natal/moment/solar_arc/secondary_progression
  - /v1/transit supports transit aspects between frame_a and frame_b
  - /v1/timeline supports timeline_type transit/secondary_progression/solar_arc with bodies list and lunations/eclipses tokens
  - Adaptive scan used for timelines; no step params
  - Envelope responses stable; lunations CSV bundled and referenced

#### S2 Notes — Transit Endpoint
- transit_type only supports "transit".
- Requires frame_a and frame_b; computes cross-aspects only.
- metadata.output does not exist.

#### S2 Notes — Timeline Endpoint
- metadata.timeline_type: transit | secondary_progression | solar_arc.
- metadata.bodies required for transit/solar_arc; accepts outer planets + jupiter/saturn + nodes; "nodes" normalized to nn/sn.
- Lunations/eclipses supported via bodies tokens in transit timeline.
- Adaptive scan down to minute; no step/step_years parameters.

### S3 — Release / Stable
- goal: Stabilize API and documentation for public release.
- exit_criteria:
  - Versioned docs and stable contract
  - Backward compatibility policy enforced

## TASKS (Living)

### BACKLOG

#### T-20260201-01 S3 docs + examples
- intent: Publish stable docs and envelope examples for public release.
- plan_refs:
  - SPEC/C_Distribute.md#C3
  - SPEC/B_Develop.md#STAGES
- implement_path:
  - SPIN/docs/
  - SPIN/styx-api/README.md
- acceptance:
  - Versioned docs and example payloads for each endpoint
  - Envelope shape documented
- steps:
  - Create SPIN/docs/ with a versioned overview
  - Add example requests/responses for each endpoint
- done_check:
  - [ ] implemented
  - [ ] basic test / verification
  - [ ] docs updated (if needed, via DUP)

#### T-20260201-02 Compatibility + deprecation policy
- intent: Define backward compatibility and deprecation rules for the API.
- plan_refs:
  - SPEC/C_Distribute.md#C3
- implement_path:
  - SPIN/docs/compatibility.md
- acceptance:
  - Compatibility policy documented and referenced in README
- steps:
  - Draft policy and deprecation timeline
  - Review with stakeholders
- done_check:
  - [ ] implemented
  - [ ] basic test / verification
  - [ ] docs updated (if needed, via DUP)

### CURRENT

- None (S3 stabilization).

### COMPLETED

#### T-20260126-08 Aspects (major set)
- intent: Add aspects with explicit orb table and meta echoing.
- plan_refs:
  - SPEC/A_Design.md#A1
- implement_path:
  - SPIN/styx-api
- acceptance:
  - Aspects array present with default major set
  - Orb table exposed in meta
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-09 Points: Lilith (mean/true toggle)
- intent: Add points.lilith with settings toggle.
- plan_refs:
  - SPEC/A_Design.md#A1
- implement_path:
  - SPIN/styx-api
- acceptance:
  - Lilith present when enabled
  - Settings toggle documented
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-10 /v1/transit skeleton
- intent: Implement /v1/transit relationship modes and base calculated outputs.
- plan_refs:
  - SPEC/A_Design.md#A1
- implement_path:
  - SPIN/styx-api
- acceptance:
  - /v1/transit accepts transit_type and returns aspects per mode
  - Aspects computed between frames
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260128-01 Calculated charts: timeline/eclipses/progressions
- intent: Implement calculated chart outputs for timelines and progressions.
- plan_refs:
  - SEED/STYX.md#C-Output-Types-and-Timelines
- implement_path:
  - SPIN/styx-api
- acceptance:
  - Timeline events use Level 1/2 definitions
  - Progression timeline returns range-based events
  - Lunations/eclipses sourced from CSV
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-01 Seed to SPEC scaffold
- intent: Create SPEC skeleton and snapshot after seed normalization.
- plan_refs:
  - SPEC/B_Develop.md#STAGES
- implement_path:
  - SPEC/
  - SEED/snapshot.md
- acceptance:
  - SPEC files created from template
  - Snapshot created and kept short
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-02 Create SPIN workspace
- intent: Create SPIN folders for deliverable, local, and logs.
- plan_refs:
  - SPEC/B_Develop.md#STAGES
- implement_path:
  - SPIN/
- acceptance:
  - SPIN/styx-api, SPIN/_local, SPIN/_logs exist
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-03 Bootstrap FastAPI app
- intent: Create base app, config, and routing skeleton in SPIN/styx-api.
- plan_refs:
  - SPEC/A_Design.md#A2
- implement_path:
  - SPIN/styx-api
- acceptance:
  - App starts; /v1/health returns OK
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-04 Implement /v1/config
- intent: Return catalogs and defaults from seed.
- plan_refs:
  - SPEC/A_Design.md#A1
- implement_path:
  - SPIN/styx-api
- acceptance:
  - /v1/config returns asteroid list and defaults
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-05 Implement /v1/chart core
- intent: Compute bodies, houses, points, nodes, stars.
- plan_refs:
  - SPEC/A_Design.md#A1
- implement_path:
  - SPIN/styx-api
- acceptance:
  - MVP payload returned with deterministic ordering
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-06 Geocoding adapter + stub
- intent: Resolve place strings; support STYX_GEOCODE_STUB for tests.
- plan_refs:
  - SPEC/A_Design.md#A3
- implement_path:
  - SPIN/styx-api
- acceptance:
  - Place strings resolve or return 422
  - Stub works for offline tests
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

#### T-20260126-07 Tests for MVP endpoints
- intent: Ensure determinism and schema coverage.
- plan_refs:
  - SPEC/B_Develop.md#OVERVIEW
- implement_path:
  - SPIN/styx-api
- acceptance:
  - pytest -q passes
- done_check:
  - [x] implemented
  - [x] basic test / verification
  - [x] docs updated (if needed, via DUP)

### RELEASE-CHECKLIST

## LOG (Append-only)

### [2026-01-26 16:47] Session 01
- scope_level: SPEC
- summary: Created SPEC skeleton and SEED/snapshot.md after seed normalization.
- llm_reasoning_summary: Followed ReSpec Kickstart creation step to initialize governed docs.
- human_llm_conversation_summary: User approved continuing with SPEC and snapshot creation.
- decisions:
  - Proceeded with template-based SPEC files and a short snapshot.
- files_touched:
  - SPEC/A_Design.md
  - SPEC/B_Develop.md
  - SPEC/C_Distribute.md
  - SEED/snapshot.md
- terminal_summary_id: TS-20260126-01

### [2026-01-26 16:47] Terminal Summary TS-20260126-01
- commands: New-Item SPEC; Set-Content SPEC/A_Design.md; Set-Content SPEC/C_Distribute.md; Set-Content SEED/snapshot.md; Set-Content SPEC/B_Develop.md
- exit_codes: all 0
- stdout_summary: Directories/files created.
- stderr_summary: none

### [2026-01-26 16:51] Session 02
- scope_level: SPIN
- summary: Created SPIN workspace and updated SPEC/SEED summaries for spin phase.
- llm_reasoning_summary: Entered Spin phase and aligned living docs and tasks to seed scope.
- human_llm_conversation_summary: User requested sequential execution of SPIN creation, SPEC updates, and task planning.
- decisions:
  - Set current stage to S1 and queued MVP implementation tasks.
- files_touched:
  - SPIN/
  - SPEC/A_Design.md
  - SPEC/B_Develop.md
  - SPEC/C_Distribute.md
  - SEED/snapshot.md
- terminal_summary_id: TS-20260126-02

### [2026-01-26 16:51] Terminal Summary TS-20260126-02
- commands: New-Item SPIN; Set-Content SPEC/A_Design.md; Set-Content SPEC/C_Distribute.md; Set-Content SEED/snapshot.md; Set-Content SPEC/B_Develop.md
- exit_codes: all 0
- stdout_summary: SPIN directories created; SPEC/SEED updated.
- stderr_summary: none

### [2026-01-28 23:20] Session 03
- scope_level: SPIN
- summary: Hardened /v1/chart and /v1/transit, added astrocartography results, moved runtime assets/logs, and simplified response meta per requirements.
- llm_reasoning_summary: Implemented user-requested payload changes, added astrocartography computation with dataset support, and aligned SPIN structure with updated delivery rules.
- human_llm_conversation_summary: User directed response schema changes, transit mode expansion, astrocartography behavior, ephe/log placement, and generic ReSpec updates.
- decisions:
  - Keep deliverable-only assets under SPIN/styx-api and move scratch/venv/caches to SPIN/_local.
  - Astrocartography uses cities dataset with top-N nearest by orb; location not required.
  - Config centralizes defaults/aspects/provenance; meta trimmed to essentials.
- files_touched:
  - SPIN/styx-api/app/main.py
  - SPIN/styx-api/app/services/astro.py
  - SPIN/styx-api/app/services/geocode.py
  - SPIN/styx-api/app/models.py
  - SPIN/styx-api/tests/test_api.py
  - SPIN/styx-api/data/cities5000.txt
  - SPIN/styx-api/data/countryInfo.txt
  - SPIN/styx-api/tests/fixtures/cities.txt
  - SPIN/styx-api/tests/fixtures/countries.txt
  - SPIN/styx-api/pyproject.toml
  - SEED/reSpec.md
- terminal_summary_id: TS-20260128-01

### [2026-01-28 23:20] Terminal Summary TS-20260128-01
- commands: Move-Item SPIN/_local/ephe -> SPIN/styx-api/ephe; Move-Item uvicorn logs -> SPIN/_logs; pytest -q; Invoke-WebRequest cities5000.zip/countryInfo.txt; Move-Item .venv/.pytest_cache/__pycache__ -> SPIN/_local
- exit_codes: all 0 (last pytest passed)
- stdout_summary: Runtime assets/logs moved; datasets downloaded; tests passing.
- stderr_summary: none

### [2026-01-29 00:40] Session 04
- scope_level: SPIN
- summary: Finalized astrocartography with country names, orb filtering, and crossings output.
- llm_reasoning_summary: Added country-name mapping, max-orb filter, and crossings list to improve astrocartography usefulness.
- human_llm_conversation_summary: User requested full country names and crossings like Pluto/Nodes; accepted defaults and asked to log completion.
- decisions:
  - Astrocartography filters results by max orb (default 2.0; env override).
  - Add crossings list with bodies + nodes + angles and top-N cap.
  - Country names resolved via countryInfo dataset.
- files_touched:
  - SPIN/styx-api/app/services/astro.py
  - SPIN/styx-api/app/main.py
  - SPIN/styx-api/tests/test_api.py
  - SPIN/styx-api/tests/fixtures/countries.txt
  - SPIN/styx-api/data/countryInfo.txt
- terminal_summary_id: TS-20260129-01

### [2026-01-29 00:40] Terminal Summary TS-20260129-01
- commands: pytest -q
- exit_codes: all 0
- stdout_summary: Tests passing after astrocartography updates.
- stderr_summary: none

### [2026-01-29 01:10] Session 05
- scope_level: SPEC
- summary: Updated S2 notes for astrocartography crossings and solar arc sun mode; marked transit skeleton task done.
- llm_reasoning_summary: User requested doc updates after completing astrocartography and solar arc work.
- human_llm_conversation_summary: User asked to log completed work and proceed with secondary progression next.
- decisions:
  - Treat /v1/transit skeleton as completed.
- files_touched:
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260129-02

### [2026-01-29 01:10] Terminal Summary TS-20260129-02
- commands: n/a (doc update)
- exit_codes: n/a
- stdout_summary: Updated living notes and task status.
- stderr_summary: none

### [2026-01-29 02:05] Session 06
- scope_level: SPIN
- summary: Implemented secondary progression aspects (day-for-year) and updated docs.
- llm_reasoning_summary: Added progressed chart computation for secondary progression and aspects vs natal; kept response as aspects list.
- human_llm_conversation_summary: User requested to continue after astrocartography and proceed with secondary progression.
- decisions:
  - Use day-for-year progression based on natal timestamp and target timestamp.
- files_touched:
  - SPIN/styx-api/app/main.py
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260129-03

### [2026-01-29 02:05] Terminal Summary TS-20260129-03
- commands: pytest -q
- exit_codes: all 0
- stdout_summary: Tests passing after secondary progression update.
- stderr_summary: none

### [2026-01-29 02:20] Session 07
- scope_level: SPEC
- summary: Logged user confirmation that astrocartography is complete; prepared to continue with next S2 item.
- llm_reasoning_summary: User requested doc/log update after finishing astrocartography.
- human_llm_conversation_summary: User marked astrocartography done and asked to proceed with item 2.
- decisions:
  - Record astrocartography completion status in living log.
- files_touched:
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260129-04

### [2026-01-29 02:20] Terminal Summary TS-20260129-04
- commands: n/a (doc update)
- exit_codes: n/a
- stdout_summary: Logged astrocartography completion and next-step intent.
- stderr_summary: none

### [2026-01-29 02:35] Session 08
- scope_level: SPIN
- summary: Added secondary progression chart-only output option.
- llm_reasoning_summary: User requested progressed chart without aspects for easier validation.
- human_llm_conversation_summary: User asked for a progressed chart output without transit aspects.
- decisions:
  - `secondary_progression` accepts `metadata.output = chart`.
- files_touched:
  - SPIN/styx-api/app/models.py
  - SPIN/styx-api/app/main.py
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260129-05

### [2026-01-29 02:35] Terminal Summary TS-20260129-05
- commands: n/a (code+doc update)
- exit_codes: n/a
- stdout_summary: Added chart-only secondary progression output.
- stderr_summary: none

### [2026-01-29 03:05] Session 09
- scope_level: SPEC
- summary: Marked completed charts/transits and recorded remaining calculated items.
- llm_reasoning_summary: User confirmed tests for synastry and requested end-of-session checklist/log update.
- human_llm_conversation_summary: User asked to mark completed endpoints and capture notes before closing session.
- decisions:
  - Treat all chart and transit modes as completed for S2 tracking.
  - Leave calculated outputs pending.
- files_touched:
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260129-06

### [2026-01-30 15:35] Session 10
- scope_level: SPEC
- summary: Marked eclipses outputs as LLM workflow via lunations CSV and updated calculated chart notes.
- llm_reasoning_summary: User opted to avoid API-side eclipse events/transit generation in favor of lunations CSV + LLM requests.
- human_llm_conversation_summary: User approved documenting eclipses handling via lunations CSV.
- decisions:
  - Treat eclipses and eclipse_transits as handled by lunations CSV + LLM workflow (no API calc).
- files_touched:
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260130-01

### [2026-01-30 20:57] Session 11
- scope_level: SPEC
- summary: Updated Level 1/2/3 timeline definitions and removed node timeline from calculated outputs.
- llm_reasoning_summary: Aligned calculated outputs with user-defined levels and moved nodes to transit outputs only.
- human_llm_conversation_summary: User requested Level 1 (outer), Level 2 (Saturn+Jupiter), Level 3 (lunations) with nodes removed from timeline.
- decisions:
  - Level 1: outer planets only.
  - Level 2: Saturn + Jupiter.
  - Level 3: lunations CSV + LLM workflow.
- files_touched:
  - SPEC/B_Develop.md
- terminal_summary_id: TS-20260130-02

### [2026-01-30 20:57] Terminal Summary TS-20260130-02
- commands: n/a (doc update)
- exit_codes: n/a
- stdout_summary: Updated S2 calculated levels and notes.
- stderr_summary: none

### [2026-01-30 22:09] Session 12
- scope_level: SPIN
- summary: Reworked secondary progression timeline output to match transit timeline schema and added tests.
- llm_reasoning_summary: Aligned progression timeline with the same event/phase structure used by transit timeline for readability and consistency.
- human_llm_conversation_summary: User requested secondary progression timeline in the same format as transit timeline with station info.
- decisions:
  - Progression timeline returns transit/natal/aspect plus phases with exact_index.
  - Outer planets excluded from progression timeline.
- files_touched:
  - SPIN/styx-api/app/services/progression_timeline.py
  - SPIN/styx-api/app/models.py
  - SPIN/styx-api/app/main.py
  - SPIN/styx-api/tests/test_api.py
  - SPIN/styx-api/app/config.py
- terminal_summary_id: TS-20260130-03

### [2026-01-30 22:09] Terminal Summary TS-20260130-03
- commands: pytest -q
- exit_codes: all 0
- stdout_summary: All tests passing after progression timeline changes.
- stderr_summary: none

### [2026-01-30 23:10] Session 13
- scope_level: SPIN
- summary: Normalized endpoint latency + description logging into a single JSON file under SPIN/_logs.
- llm_reasoning_summary: Consolidated per-endpoint latency into endpoint_descriptions.json for easier Kharon reference.
- human_llm_conversation_summary: User requested log consolidation and updated to-do tracking before ending the day.
- decisions:
  - Maintain endpoint descriptions with a single Latency_in_ms key per entry.
- files_touched:
  - SPIN/_logs/endpoint_descriptions.json
- terminal_summary_id: TS-20260130-04

### [2026-01-30 23:10] Terminal Summary TS-20260130-04
- commands: python -c (endpoint_descriptions normalization)
- exit_codes: all 0
- stdout_summary: endpoint_descriptions.json updated and latency keys normalized.
- stderr_summary: none

### [2026-02-01 10:50] DUP Entry DUP-20260201-01
- target:
  - SPEC/A_Design.md (OVERVIEW, A1, A2, A3)
  - SPEC/B_Develop.md (OVERVIEW, STAGES, TASKS, S2 notes)
  - SPEC/C_Distribute.md (OVERVIEW, C1, C2, C3)
  - SEED/STYX.md (Project Brief, Deliverables, Constraints, Acceptance, API Surface, Response/Output Types)
  - SEED/snapshot.md (full refresh)
- change_intent:
  - Align design scope to current endpoints: /v1/health, /v1/config, /v1/chart, /v1/transit, /v1/timeline, /v1/progression_timeline.
  - Document envelope responses (meta/settings/input_summary/data/timing/errors) and deterministic rounding to 2 decimals for chart/transit outputs.
  - Record astrocartography data inputs (cities5000 + countryInfo), crossings output, and lunations CSV workflow for level3/eclipses.
  - Update interaction rules: location input supports place string, object, and auto/ip; timestamp_utc supports "now" where applicable; geocode/geoip failures -> 422.
  - Refresh stages/tasks to reflect S2 completion and S3 stabilization focus; update distribution deliverables/metrics accordingly.
- applied_edits:
  - Updated SPEC/A_Design.md, SPEC/B_Develop.md, and SPEC/C_Distribute.md to reflect envelope responses, current endpoints, and S3 focus.
  - Refreshed SEED/STYX.md and SEED/snapshot.md to match current API scope, datasets, and timeline/progression behavior.

### [2026-02-01 10:50] Session 14
- scope_level: SPEC
- summary: Updated SEED/SPEC living docs to match current API scope, envelope responses, datasets, and S3 focus.
- llm_reasoning_summary: Aligned governed docs with implemented endpoints, workflows, and release stage for accurate handoff.
- human_llm_conversation_summary: User approved updating SPEC and seed files to the latest state.
- decisions:
  - Treat S2 as complete and move focus to S3 stabilization.
  - Standardize documentation around envelope responses and CSV-backed lunations/eclipses.
- files_touched:
  - SPEC/A_Design.md
  - SPEC/B_Develop.md
  - SPEC/C_Distribute.md
  - SEED/STYX.md
  - SEED/snapshot.md
- terminal_summary_id: TS-20260201-01

### [2026-02-01 10:50] Terminal Summary TS-20260201-01
- commands: apply_patch (SPEC/A_Design.md, SPEC/B_Develop.md, SPEC/C_Distribute.md); Set-Content SEED/STYX.md; Set-Content SEED/snapshot.md
- exit_codes: all 0
- stdout_summary: Updated SPEC and SEED living docs and refreshed snapshot.
- stderr_summary: none

### [2026-02-02 17:14] DUP Entry DUP-20260202-01
- target:
  - SPEC/A_Design.md (OVERVIEW, A1, A2, A3)
  - SPEC/B_Develop.md (OVERVIEW, STAGES, S2 notes)
  - SPEC/C_Distribute.md (OVERVIEW, C1, C2, C3)
  - SEED/STYX.md (full refresh)
  - SEED/snapshot.md (full refresh)
- change_intent:
  - Align design/seed scope to latest API: /v1/health, /v1/config, /v1/chart, /v1/transit, /v1/timeline; chart types include natal/moment/solar_arc/secondary_progression; unify timelines and remove deprecated modes/endpoints.
  - Remove legacy fields and tighten request/response descriptions to current shapes (transit only, timeline bodies, lunations/eclipses tokens).
  - Refresh distribution and snapshot to match S3 focus.
- applied_edits:
  - Updated SPEC/A_Design.md and SPEC/B_Develop.md to reflect unified timelines, transit-only, and removed legacy fields.
  - Updated SPEC/C_Distribute.md deliverables to remove progression_timeline and non-transit modes.
  - Refreshed SEED/STYX.md and SEED/snapshot.md to match latest API scope and examples.
