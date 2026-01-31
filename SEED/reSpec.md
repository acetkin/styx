# ReSpec

version: V3-1

## Table of Contents (TOC)

- **A. General Rules**
  - A1. Scope and Language
  - A2. Source of Truth and Human Approval
  - A3. Document Behavior Types
- **B. Structure**
  - B1. Folder Structure and ReSpec Points
    - Three-Root Repository Rule
    - Fixed SPEC Folder Structure
    - Summary Layers (Documents and Logs)
    - ReSpec Points
  - B2. SPEC/ File Definitions
    - SPEC/ (root files)
  - B3. SPIN/ Output Types
- **C. Instructions**
  - C1. ReSpec Flow Phases
    - Phase 1: Kickstart Phase
      - Kickstart without seed file
      - Kickstart seed file
    - Phase 2: Restart Phase
    - Phase 3: Spin Phase
    - Phase 4: Iteration Phase
  - C2. Document Protocols
    - Document Templates
      - `SEED/<seed>.md`
      - `SEED/snapshot.md`
      - `SPEC/A_Design.md`
      - `SPEC/B_Develop.md`
      - `SPEC/C_Distribute.md`
    - Document Creation Protocol
    - Document Update Protocol
  - C3. Agent Modes
    - General Definitions
    - Code Agent

---

# A. General Rules

## A1. Scope and Language

- ReSpec defines a generic operating workflow for producing **Code** outputs (software systems, APIs, plugins, apps).

- ReSpec exists for three purposes:

  1. **General document system:** Standardize the document structure, templates, deterministic creation (DCP), and controlled updates (DUP) so both humans and LLMs can follow the project consistently.
  2. **Project phasing:** Systematize iterations by defining deterministic phases and state-based transitions across the project lifecycle.
  3. **Log & continuity:** Preserve cross-session continuity and project evolution through a structured history and evidence trail.

- In conversations with AI, the human may write in any language.

- All project files are **English-only**.

$1- **ReSpec file normalization:** If the provided ReSpec rules file has a different name, copy it into `SEED/reSpec.md` and treat that file as the single source of truth. After the copy, remove the original non-canonical rules file to avoid drift.

- $1- **ReSpec file normalization:** If the provided ReSpec rules file has a different name, copy it into `SEED/reSpec.md` and treat that file as the single source of truth. After the copy, remove the original non-canonical rules file to avoid drift.
- Human approval is required **before** modifying any file under `SEED/` or `SPEC/`.
- Logs are for continuity and traceability; keep them concise and referenceable.

## A3. Document Behavior Types

- **Directive** documents define stable rules and must not be modified by the VS Code LLM (examples: `SEED/reSpec.md`, naming/folder invariants). Directive files may be changed only by the human; the LLM may propose changes via DUP but must not apply them.
- **Living** documents represent the current working state or operational plan and may be overwritten when updated (examples: `SPEC/A_Design.md`, `SPEC/B_Develop.md`, `SPEC/C_Distribute.md`, `SEED/snapshot.md`).
- **Log** documents record irreversible history and must be append-only (examples: append-only log sections such as `## LOG`).
- **Hybrid (Living + Log sections)** documents combine an overwritable working header with an append-only log section (examples: `SPEC/B_Develop.md` where `## LOG` is append-only).

In this system, do not introduce ad-hoc standalone decision/history log files; the canonical log lives in `SPEC/B_Develop.md#LOG` (when `SPEC/` exists). `SEED/snapshot.md` is a **Living**, self-contained handoff snapshot used to bootstrap a Restart even when `SPEC/` is missing. `SPIN/_logs/` is not canonical; it is a sandbox for raw LLM traces that may be summarized and promoted into `SPEC/B_Develop.md#LOG` when needed.

---

# B. Structure

## B1. Folder Structure and ReSpec Points

### Three-Root Repository Rule

- Every ReSpec project repository uses exactly three top-level roots: `SEED/`, `SPEC/`, and `SPIN/`.
- `SEED/` holds project identity + minimal continuity snapshots.
- `SPEC/` holds process rules and planning documents.
- `SPIN/` holds produced outputs and working artifacts.

### Repository Root Layout Rules

- Repo root MUST contain:
  - `SEED/`
  - `SPEC/`
  - `SPIN/`
  - GitHub-required infra at root (do not move under `SPIN/`):
    - `.github/`
    - `.gitignore`
    - `.gitattributes`
- Docs location rule:
  - Project documentation lives under `SPIN/docs/`.
  - If `docs/` exists at root, move it to `SPIN/docs/`.
- Logging rule:
  - Operational logs and generated samples go under `SPIN/_logs/`.
  - Example: `SPIN/_logs/repo_reorg/<timestamp>/...`

**Rationale**

- `.github/` must stay at repo root for GitHub Actions/workflows to run reliably.
- Keeping `SEED/`, `SPEC/`, and `SPIN/` at root keeps navigation stable; keeping docs/logs under `SPIN/` keeps the root clean.

### Fixed SPEC Folder Structure

- `SPEC/` is fixed and predictable to support reliable LLM navigation and updates.
- `SPEC/` contains **only** three governed top-level summary documents. No subfolders under `SPEC/` are allowed.

```text
/
  SEED/
    reSpec.md
    <seed>.md
    snapshot.md

  SPEC/
    A_Design.md
    B_Develop.md
    C_Distribute.md

  SPIN/
    <deliverable>/
      (submission-ready outputs only)
    _local/
      (non-submission artifacts)
    _logs/
      (non-submission artifacts)
```

### Summary Layers (Documents and Logs)

ReSpec uses layered summaries to make navigation and restarts deterministic.

**Document summary layers (Living):**

- **Level 1:** `SEED/<seed>.md` — the project seed; the single compact source that can be expanded into the layers below.
- **Level 2:** `SPEC/A_Design.md`, `SPEC/B_Develop.md`, `SPEC/C_Distribute.md` — decomposed, higher-level working summaries derived from the seed.
- **Level 3:** Detailed sections inside the Level 2 files (not separate files), e.g. `A1/A2/A3` sections in `A_Design.md`, `STAGES/TASKS/LOG` sections in `B_Develop.md`, and `C1/C2/C3` sections in `C_Distribute.md`.

**Log layers (Hybrid/Log):**

- **Level 1:** `SEED/snapshot.md` — a short, self-contained handoff snapshot for cross-session continuity and Restart bootstrapping (no required refs into `SPEC/`).
- **Level 2:** `SPEC/B_Develop.md#LOG` — the canonical project history when `SPEC/` exists (append-only).
- **Level 3:** `SPIN/_local/` and `SPIN/_logs/` — non-submission evidence, experiments, terminal traces, and LLM scratch logs; promote durable items by summarizing them into `SPEC/B_Develop.md#LOG`.

### ReSpec Points

- **Scope levels:** The scope level defines which roots are allowed to change in the current iteration.
- A higher scope may still update earlier roots when needed.
- Levels:
  - **SEED respec point**: includes `SEED/`
  - **SPEC respec point**: includes `SEED/ + SPEC/`
  - **SPIN respec point**: includes `SEED/ + SPEC/ + SPIN/`

## B2. SPEC/ File Definitions

`SPEC/` is the governed project workspace. It contains **only** three fixed top-level files and no subfolders.

#### **SPEC/ (root files)**

- `A_Design.md` — **Living**: Design-layer operating brief and decomposition. Contains `A1/A2/A3` as sections:
  - `## A1 — Features`
  - `## A2 — Architecture`
  - `## A3 — Interaction`

- `B_Develop.md` — **Hybrid (Living + Log sections)**: Implementation strategy + execution hub. Contains:
  - **Living sections**: `## OVERVIEW`, `## STAGES`, `## TASKS` (overwritable)
  - **Log section**: `## LOG` (append-only canonical history: sessions, terminal summaries, decisions, DUP entries)

- `C_Distribute.md` — **Living**: Distribution and release strategy. Contains `C1/C2/C3` as sections:
  - `## C1 — Stage 1 (Early/Internal)`
  - `## C2 — Stage 2 (Beta/Feedback)`
  - `## C3 — Stage 3 (Stable/Public)`

---

## B3. SPIN/ Output Types

### General Rules

- `SPIN/` is the production/output workspace and is free-form internally.
- `SPIN/<deliverable>/` is **submission-ready only** (handoff/publish/shippable). All code, tests, configs, scripts, and any runtime-required assets MUST live under `SPIN/<deliverable>/` (never at repo root). Keep it clean: only finalized assets and required packaging. Drafts, notes, resources, links, and planning artifacts belong in `SPEC/` (not in `SPIN/<deliverable>/`).
- `SPIN/_local/` contains **non-submission artifacts** created during development (scratch work, temporary exports, experiments, local notes, debug outputs).
- `SPIN/_logs/` is the LLM’s sandbox for non-submission logs and scratch traces during development. These logs may be summarized and promoted into `SPEC/B_Develop.md#LOG` when they contain durable decisions, findings, or reproducible evidence; otherwise they remain local and non-deliverable. Server/runtime logs belong here.

### Typical Outputs

- Outputs in `SPIN/<deliverable>/` MUST be submission-ready and directly handoff/publish/shippable.
- Intermediates, drafts, and tool outputs belong in `SPIN/_local/` until they become deliverable-ready.
- LLM sandbox logs and scratch traces belong in `SPIN/_logs/`; promote durable findings/decisions by summarizing them into `SPEC/B_Develop.md#LOG`.
- Examples (in `SPIN/<deliverable>/`): packaged releases (zip/app), delivery build artifacts, demo bundles, generated API docs, sample payloads, publish-ready media, and submission-ready source bundles (code + tests + configs + scripts).

### Do not store in SPIN/:

- Secrets/keys, credentials, or tokens (never commit).
- Large caches or machine-specific junk (keep out of the repo; use `.gitignore` where relevant).
- Tool output that cannot be reproduced or traced (prefer reproducible workflows and referenceable logs).

# C. Instructions

## C1. ReSpec Flow Phases

This section defines deterministic phases of work based on repository state (which roots/files exist). There is **no special state-transition command**; phases advance by creating the required files/folders (with human approval where required).

### Phase 1: Kickstart Phase

- **Starting state (Kickstart):** `SEED/reSpec.md` exists. `SPEC/` and `SPIN/` do not exist yet.
- **Goal:** Ensure the SEED seed identity file exists (`SEED/<seed>.md`), then prepare to initialize the fixed `SPEC/` skeleton and the snapshot file `SEED/snapshot.md` **without** producing submission-ready work.
- **Stop rule:** When the SEED seed identity file (`SEED/<seed>.md`) is complete and the next step is to create or modify anything under `SEED/` or `SPEC/`, stop and request human approval (A2).

$1- **Seed import rule:** If a seed identity file is provided externally, place it into `SEED/` **without modifying its contents**. Treat it as authoritative input; any improvements must be proposed separately via DUP and approved by the human, not edited during import.

(Note: Means the current project will be developed in VS Code with an LLM.)

- **Entry condition:** No seed identity file exists in `SEED/` besides `reSpec.md`.
- **Required action:** If `SEED/` contains any `.md` besides `reSpec.md`, read it and treat it as the seed identity file (`SEED/<seed>.md`). Otherwise, request human approval (A2), then create `SEED/<seed>.md` using **C2 → Document Templates**.
- **Output rule:** Do not create `SPEC/` or `SPIN/` until the seed identity file (`SEED/<seed>.md`) is completed and approved.

$1- **Seed import rule:** If a seed identity file is provided externally, place it into `SEED/` **without modifying its contents**. Treat it as authoritative input; any improvements must be proposed separately via DUP and approved by the human, not edited during import.

(Note: Means the seed file is developed with an LLM outside VS Code such as a ChatGPT phone app. The current project will be developed with the given seed file.)

- **Entry condition:** `SEED/` contains a seed identity file (a `.md` besides `reSpec.md`), treated as `SEED/<seed>.md`.
- **Required action:** Review the seed identity file (`SEED/<seed>.md`) for completeness and consistency with A/B sections.
- **Next step:** With human approval, initialize the fixed `SPEC/` skeleton and create `SEED/snapshot.md` before any production begins.

### Phase 2: Restart Phase

- **Starting state:** `SEED/reSpec.md`, the seed identity file (`SEED/<seed>.md`), and `SEED/snapshot.md` exist. `SPEC/` and `SPIN/` do not exist (or were removed).
- **Goal:** Restore the fixed `SPEC/` skeleton and refresh `SEED/snapshot.md` (keep it short and self-contained) **without** producing submission-ready work.
- **Operating rule:** Any creation/modification under `SEED/` or `SPEC/` requires human approval (A2). Once `SPEC/` is restored, record the work by appending a Session entry in `SPEC/B_Develop.md#LOG`.

### Phase 3: Spin Phase

- **Starting state:** `SEED/` and `SPEC/` exist, including `SEED/snapshot.md`. `SPIN/` does not exist.
- **Goal:** Create `SPIN/` and begin production.
- **Output rule:** All submission-ready outputs go to `SPIN/<deliverable>/`. All non-submission artifacts stay out of `SPIN/<deliverable>/` and belong in `SPIN/_local/` or `SPIN/_logs/` (see B3).

### Phase 4: Iteration Phase

- **Starting state:** `SEED/`, `SPEC/`, and `SPIN/` exist. Production is active.
- **Goal:** Continue iterative work while keeping documentation updates controlled and traceable.
- **Operating rules:**
  - Changes to `SEED/` or `SPEC/` require human approval (A2) and must be logged in `SPEC/B_Develop.md#LOG`.
  - Logs are append-only; do not rewrite history (A2, B2).
  - Keep `SEED/snapshot.md` as a short, overwritable, self-contained handoff snapshot (do not rely on links/refs into `SPEC/`).

## C2. Document Protocols

This section defines the canonical file templates and the controlled update protocol used for `SEED/` and `SPEC/`.

### Document Templates

#### SEED seed identity file (`SEED/<seed>.md`) (identifier: "seed")

Use this template when creating or refreshing the SEED seed identity file (`SEED/<seed>.md`). The identity identifier is "seed", but the file name is not fixed. It must be concise and complete.

```text
# Seed
## Project Identity
name:
output_family: Code

## Project Brief

**One-Sentence Description:**

**Goals:**
-

**Non-Goals:**
-

**Deliverables:**
-

**Constraints:**
-

**Acceptance Criteria:**
-

**Notes for SPEC Planning:**
-

**Suggested SPIN Output:**
deliverable_folder_name:

## A_Design (Seed Summary)
- A1_features:
- A2_architecture:
- A3_interaction:

## B_Develop (Seed Summary)
- overview:
- stages:
- tasks_focus:
- logging_focus:

## C_Distribute (Seed Summary)
- c1_stage_1:
- c2_stage_2:
- c3_stage_3:
```

#### SEED/snapshot.md (living snapshot)

- `SEED/snapshot.md` is a **Living** snapshot file and may be overwritten.
- It must stay short and fully self-contained (no required links/refs into `SPEC/`).

**Snapshot template**

```text
ReSpec Snapshot
phase: <kickstart | restart | spin | iteration>
active_deliverable: <name | NONE>
snapshot_date: <YYYY-MM-DD>
snapshot_author: <human | LLM>

status_1p: <1 short paragraph>

key_decisions:
- <decision 1 — why + impact>
- <decision 2>

recent_findings:
- <finding 1>
- <finding 2>

open_questions:
- <question 1>
- <question 2>

blockers:
- <blocker 1>
- <blocker 2>

next_actions:
- <next action 1>
- <next action 2>
```

#### SPEC/A_Design.md (design brief)

```md
# A_Design

## OVERVIEW (Living)
- intent:
- scope:
- constraints:
- success_definition:
- key_decisions:

## A1 — Features (Living)
- feature_list:

## A2 — Architecture (Living)
- boundaries:
- components:
- data_flows:

## A3 — Interaction (Living)
- interaction_rules:
- error_handling:
```

#### SPEC/B_Develop.md (hybrid execution hub: stages + tasks + history)

`B_Develop.md` is the single governed execution hub. It contains overwritable planning sections and an append-only canonical log.

```md
# B_Develop

## OVERVIEW (Living)
- implementation_strategy:
- quality_bar:
- packaging_policy:
- test_policy:

## STAGES (Living)
- current_stage: <S0 | S1 | S2 | S3>
- next_stage: <S1 | S2 | S3 | NONE>
- active_deliverable: <from SEED/<seed>.md>

### S0 — Setup / Alignment
- goal:
- exit_criteria:
  -

### S1 — MVP / First Working Slice
- goal:
- exit_criteria:
  -

### S2 — Hardening / Feedback Loop
- goal:
- exit_criteria:
  -

### S3 — Release / Stable
- goal:
- exit_criteria:
  -

## TASKS (Living)

### BACKLOG

### CURRENT

#### T-YYYYMMDD-01 <Short task title>
- intent:
- plan_refs:
  - SPEC/A_Design.md#A2
  - SPEC/B_Develop.md#OVERVIEW
- implement_path:
  - SPIN/<deliverable>/<path or module>
- acceptance:
  -
- steps:
  -
- done_check:
  - [ ] implemented
  - [ ] basic test / verification
  - [ ] docs updated (if needed, via DUP)

### RELEASE-CHECKLIST

## LOG (Append-only)

### [YYYY-MM-DD HH:MM] Session <id>
- scope_level: <SEED | SPEC | SPIN>
- summary:
- llm_reasoning_summary:
- human_llm_conversation_summary:
- decisions:
- files_touched:
- terminal_summary_id: <terminal-summary-id | NONE>

### [YYYY-MM-DD HH:MM] Terminal Summary <id>
- commands:
- exit_codes:
- stdout_summary:
- stderr_summary:

### [YYYY-MM-DD HH:MM] DUP Entry <id>
- target:
- change_intent:
- applied_edits:
```

#### SPEC/C_Distribute.md (distribution plan)

```md
# C_Distribute

## OVERVIEW (Living)
- positioning:
- channels:
- release_policy:
- versioning:

## C1 — Stage 1 (Early/Internal) (Living)
- audience:
- deliverables:
- metrics:

## C2 — Stage 2 (Beta/Feedback) (Living)
- audience:
- deliverables:
- metrics:

## C3 — Stage 3 (Stable/Public) (Living)
- audience:
- deliverables:
- metrics:
```

### Document Creation Protocol

This protocol defines how to **create the required folders/files deterministically** based on current repo state. It is used when a project is first initialized, restored, or when `SPIN/` is created for the first time.

**Governance**

- Any creation/modification under `SEED/` or `SPEC/` requires human approval (A2).
- Do not produce submission-ready outputs during **Phase 1–2** (see C1). Production begins only when entering **Phase 3: Spin Phase**.

**Creation cases (aligned with C1 phases)**

- **Phase 1: Kickstart Phase (seed authoring / seed review)**

  - If the seed identity file (`SEED/<seed>.md`) is missing: apply the Kickstart seed discovery rule from **C1** (read any `.md` besides `reSpec.md`; otherwise create `SEED/<seed>.md` using **C2 → Document Templates**).
  - Do **not** create `SPEC/` or `SPIN/` until the seed identity file (`SEED/<seed>.md`) is complete and the next step is approved.

- **Phase 1 (initialization step after seed is ready): Create SPEC files + snapshot**

  - Preconditions: `SEED/reSpec.md` and the seed identity file (`SEED/<seed>.md`) exist; `SPEC/` does not exist.
  - Actions (with human approval):
    - Create `SPEC/`.
    - Create `SPEC/A_Design.md`, `SPEC/B_Develop.md`, and `SPEC/C_Distribute.md` using the templates in **C2 → Document Templates**.
    - Create `SEED/snapshot.md` using the template in **C2 → Document Templates**.
  - Output rule: Do **not** create `SPIN/` yet.

- **Phase 2: Restart Phase (restore SPEC)**

  - Preconditions: `SEED/` exists (including `<seed>.md` and `snapshot.md`), but `SPEC/` is missing.
  - Actions (with human approval):
    - Re-create `SPEC/`.
    - Re-create `SPEC/A_Design.md`, `SPEC/B_Develop.md`, and `SPEC/C_Distribute.md` using the templates in **C2 → Document Templates**.
    - Refresh `SEED/snapshot.md` (keep it short and self-contained).
  - Output rule: Do **not** create `SPIN/` yet.

- **Phase 3: Spin Phase (create SPIN/ and start production workspace)**

  - Preconditions: `SEED/` and `SPEC/` exist; `SPIN/` does not exist.
  - Actions:
    - Create `SPIN/`.
    - Create `SPIN/_local/`.
    - Create `SPIN/_logs/`.
    - Create `SPIN/<deliverable>/` (folder name from the seed identity file: `SEED/<seed>.md → deliverable_folder_name`).
  - Output rule: Submission-ready outputs go only to `SPIN/<deliverable>/`. Non-submission artifacts go to `SPIN/_local/` and `SPIN/_logs/` (see B3).

**Logging requirement (canonical)**

- After any creation action above, append a **Session** entry to `SPEC/B_Develop.md#LOG` summarizing:
  - what was created (folders/files),
  - why (which phase/case),
  - any blockers and next actions.
- If terminal commands were used for scaffolding, also append a **Terminal Summary** entry.
- Raw terminal traces or verbose LLM traces may be stored under `SPIN/_logs/`, but the canonical project history MUST be summarized and appended to `SPEC/B_Develop.md#LOG`.

**Non-goals**

- DCP does not rename/move/extend the fixed `SPEC/` structure.
- DCP does not create additional governed docs beyond the fixed skeleton unless explicitly requested by the human.

### Document Update Protocol

DUP controls any changes to `SEED/` or `SPEC/`.

- **Trigger:** If a change to any `SEED/` or `SPEC/` file is needed, the LLM must stop and write a DUP entry in `SPEC/B_Develop.md` under `## LOG`.
- **Required fields:** Each DUP entry must specify the exact target (file + section + sentence/line anchor) and the change intent.
- **Suggested wording (recommended):** To make approval actionable, the LLM SHOULD include the exact suggested wording (as short bullets) inside `change_intent` or immediately below it in the same DUP entry.
- **Approval rule:** The LLM must wait for explicit human approval before any edit to `SEED/` or `SPEC/` is applied.
- **Apply + log:** After the human approves and the change is applied, the LLM appends the applied edit summary to the same DUP entry.

## C3. Agent Modes

### General Definitions

- Agent modes define role constraints for the LLM when producing outputs.
- The active mode MUST match the project’s `output_family` in the seed identity file (`SEED/<seed>.md`).
- The LLM MUST NOT propose changes to the fixed `SPEC/` hierarchy or fixed file names.
- The fixed structure constrains the `SPEC/` hierarchy and file names only; `SPIN/` is a free-form production area as long as:
  - outputs under `SPIN/<deliverable>/` are submission-ready, and
  - non-submission artifacts are confined to `SPIN/_local/` and `SPIN/_logs/`.
- If a different structure or output family is needed, it must be requested explicitly by the human as a structural change.
- Any changes to `SEED/` or `SPEC/` must follow DUP (C2) and be logged in `SPEC/B_Develop.md#LOG`.

### Code Agent

**Role Definition**

You are a senior software engineer and technical lead. You write clean, production-grade code and set up a reliable local development and testing workflow. You prioritize correctness, maintainability, and small safe increments. You keep the repo structure fixed as defined.

**Responsibilities**

- Implement features and fixes under `SPIN/` with a runnable path and basic tests when applicable.
- Keep architecture decisions and plans in `SPEC/`, and keep `SPIN/` release-ready (submission-ready outputs under `SPIN/<deliverable>/`).
- When uncertainty exists, propose implementation options with trade-offs (without proposing `SPEC/` structure or file-name changes) and ask for approval before breaking or structural changes.
- Use DUP (C2) and append logs to `SPEC/B_Develop.md#LOG` for any governed documentation updates.
