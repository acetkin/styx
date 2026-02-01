# C_Distribute

## OVERVIEW (Living)
- positioning: Deterministic, schema-first astrology computation API with envelope responses.
- channels: Internal dev, limited beta partners, public API release.
- release_policy: Stage-gated; expand scope only after stability and test coverage.
- versioning: SemVer for API surface, schema, and envelope compatibility.

## C1 — Stage 1 (Early/Internal) (Living)
- audience: Internal team and trusted testers.
- deliverables: SPIN/styx-api with /v1/health, /v1/config, /v1/chart, /v1/transit, /v1/timeline, /v1/progression_timeline; envelope responses; datasets (cities5000, countryInfo, lunations_100y.csv); basic tests and smoke run.
- metrics: Determinism verified; tests passing; envelope shape stable; core payloads complete.

## C2 — Stage 2 (Beta/Feedback) (Living)
- audience: Early adopters and partner integrators.
- deliverables: Performance tuning, validation hardening, expanded docs, compatibility notes, optional cache strategy.
- metrics: Low error rate; feedback integrated; API contract stable.

## C3 — Stage 3 (Stable/Public) (Living)
- audience: Public developers.
- deliverables: Stable API, versioned docs + examples, backward-compatibility policy, deprecation playbook.
- metrics: Stability, uptime targets, backward compatibility adherence.
