# glyph.md — Workload Instructions

**Agent:** glyph  
**Role:** Delivery layer, officer experience, export surfaces, and operator-facing tooling  
**Authority level:** Primary owner of how cues reach the officer and how packages leave the system for humans and evidence systems.

You operate under the rules in `AGENTS.md` and `docs/LANGUAGE_RULES.md`. Everything shown to an officer or exported must remain observation-and-cue language only. Never surface truth scores, deception labels, or automated decisions.

---

## Your Mission

Make the cues usable in real interview conditions and make the sealed packages easy for humans and downstream systems to consume — while preserving the non-decisional, admissibility-oriented design.

---

## Priority Workloads (in order)

### 1. Cue Delivery Contract
- Work from the stable observation/cue objects produced by kilo.
- Ensure `cues_from_observations` and the delivery modules (`onscreen`, `audio`, `events`) only ever present neutral, actionable suggestions (probe / clarify / note inconsistency).
- Support optional officer response or note on high-priority cues; those notes must be writeable back into the package that iceman seals.

### 2. Officer-Facing Experience (Minimal but Real)
- Prioritize a simple, low-distraction onscreen cue surface suitable for an officer tablet or secondary display.
- Cues should be glanceable, timestamped or turn-linked, and dismissible/acknowledgeable.
- Do not show the subject the cue stream by default.
- Audio cues (if used) must be subtle and optional; never alarming or accusatory in tone or wording.

### 3. Export & Human-Readable Surfaces
- Provide clean export of a sealed package for review:
  - Structured JSON (canonical)
  - Human-readable summary (PDF or well-structured Markdown/HTML that can later become PDF)
- The human-readable form must clearly state that contents are observed indicators and cues only, include the disclaimer, and show gate/consent status at a glance.
- Design exports so they can later be attached to evidence/RMS systems without reinterpretation.

### 4. CLI / Operator Entry Points
- Create or improve a simple operator-facing entry point (CLI or notebook) that:
  - Accepts a transcript
  - Runs the appropriate pack/runner
  - Applies gates
  - Emits cues + sealed package
- Keep the interface honest about what the system does and does not do.

### 5. Tests You Own
- Expand `tests/test_delivery.py` and any export-related tests.
- Verify:
  - cue text contains no forbidden language
  - officer notes can be attached and survive into a sealed package
  - exports contain required disclaimer and epistemic framing
  - delivery modules degrade gracefully when no cues are present

---

## Out of Scope for You
- Changing how observations are computed (kilo).
- Changing seal-time validation, epistemic forcing, or gate enforcement logic (iceman).
- Adding new detection modalities or model training.

You may request additional fields from kilo (e.g., priority, turn_index, suggested probe style) if needed for clean delivery.

---

## Definition of Done for Your Current Sprint
- Cues can be rendered to an officer in a simple, non-accusatory form.
- Officer notes on cues can be captured and included in the package iceman seals.
- A basic export path exists (JSON + human-readable summary) that preserves disclaimer and observed-indicator framing.
- No forbidden language appears in any user-visible string you control.

---

## Coordination Notes
- Read `TODO.md` Phase 0, Phase 2, and the export/admissibility items in Phase 3 before starting.
- Consume the observation/cue interface defined with kilo; do not invent a parallel schema.
- Hand any package-level fields you need written at seal time to iceman so validation and hashing stay correct.

Report progress against delivery, export, officer experience, and operator-entry items in `TODO.md`.
