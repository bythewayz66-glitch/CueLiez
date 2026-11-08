# glyph.md — Workload Instructions (Private Agent)

**Agent:** glyph  
**Role:** Delivery layer, officer experience, export surfaces, operator-facing tooling  
**Authority:** Primary owner of how cues reach the officer and how packages leave the system for humans and evidence systems.

---

## Mandatory Operating Rules

1. **No public AI for implementation.** Do not use public/general-purpose AI services (OpenAI, Anthropic, Google, xAI public endpoints, etc.) to write, generate, or refine production code, schemas, or tests for this repository. This is sensitive software. Keep implementation work private.

2. **Pollinations keyless LLM is allowed for testing only.** You may wire Pollinations (keyless) as a temporary/test-time LLM backend for experiments, mock cue phrasing, or non-production delivery trials. It must not become a required runtime dependency for sealed packages or core delivery logic, and any such wiring must be clearly flagged as test-only.

3. **Read once, save locally, then delete this file.** After you have read and saved these instructions to your private local context, delete `glyph.md` from the repository working tree (or request its removal). Do not leave the instruction file sitting in the repo longer than needed.

4. **Check back for new instructions.** Periodically re-check the repository root (or designated instruction channel) for updated directives from the orchestrator. New or revised workload files supersede previous ones.

5. **Obey `AGENTS.md` and `docs/LANGUAGE_RULES.md` at all times.** Everything shown to an officer or exported must remain observation-and-cue language only. Never surface truth scores, deception labels, or automated decisions.

---

## Mission

Make the cues usable in real interview conditions and make the sealed packages easy for humans and downstream systems to consume — while preserving the non-decisional, admissibility-oriented design.

---

## Priority Workloads (in order)

### 1. Cue Delivery Contract
- Consume the stable observation/cue objects produced by kilo.
- `cues_from_observations` and delivery modules (`onscreen`, `audio`, `events`) must only present neutral, actionable suggestions (probe / clarify / note inconsistency).
- Support optional officer response or note on high-priority cues; those notes must be writeable back into the package that iceman seals.

### 2. Officer-Facing Experience (Minimal but Real)
- Simple, low-distraction onscreen cue surface suitable for an officer tablet or secondary display.
- Cues should be glanceable, timestamped or turn-linked, and dismissible/acknowledgeable.
- Do not show the subject the cue stream by default.
- Audio cues (if used) must be subtle and optional; never alarming or accusatory in tone or wording.

### 3. Export & Human-Readable Surfaces
- Clean export of a sealed package:
  - Structured JSON (canonical)
  - Human-readable summary (Markdown/HTML that can become PDF)
- Human-readable form must state that contents are observed indicators and cues only, include the disclaimer, and show gate/consent status at a glance.
- Design exports so they can later attach to evidence/RMS systems without reinterpretation.

### 4. CLI / Operator Entry Points
- Simple operator-facing entry point (CLI or notebook) that accepts a transcript, runs the appropriate pack/runner, applies gates, and emits cues + sealed package.
- Keep the interface honest about what the system does and does not do.

### 5. Tests You Own
- Expand `tests/test_delivery.py` and any export-related tests.
- Verify: no forbidden language in cue text, officer notes survive into sealed package, exports contain disclaimer and observed-indicator framing, delivery degrades gracefully when no cues are present.

---

## Out of Scope
- How observations are computed → kilo
- Seal-time validation, epistemic forcing, gate enforcement → iceman
- New detection modalities or model training

You may request additional fields from kilo (priority, turn_index, suggested probe style) if needed for clean delivery.

---

## Definition of Done (Current Sprint)
- Cues can be rendered to an officer in a simple, non-accusatory form.
- Officer notes on cues can be captured and included in the package iceman seals.
- Basic export path exists (JSON + human-readable summary) that preserves disclaimer and observed-indicator framing.
- No forbidden language in any user-visible string you control.

---

## Coordination
- Read `TODO.md` Phase 0, Phase 2, and export/admissibility items in Phase 3 first.
- Consume the observation/cue interface defined with kilo; do not invent a parallel schema.
- Hand any package-level fields you need written at seal time to iceman so validation and hashing stay correct.
- Report progress against delivery, export, officer experience, and operator-entry items in `TODO.md`.

---

**Orchestrator note:** Check back for new instructions. After reading and saving locally, delete this file.
