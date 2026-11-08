# Session Lifecycle (gates, observation cycles, seal)

**Scope:** first-pilot modes emphasize `generic` and `interrogation` (government supported but not first external pilot). Observation and cues only — never findings.

## API (`cueliez.session` / `cueliez.gates`)

1. **`start_session(state: SessionGateState) -> SessionGateState`** — fail-closed checks (prohibited uses, consent, training for mode) before session start.
2. **`assert_can_observe(state: SessionGateState) -> None`** — same fail-closed checks before observation/runners execute. **Safe to call repeatedly** (e.g., before each observation cycle in real-time/streaming flows) as long as gate state remains satisfied.
3. Build observation package(s) from transcripts via runners (`default_runner`/`full_runner`).
4. **Attach officer notes before seal** if used: `attach_officer_cue_notes(...)` on the **unsealed** package. Sealed packages refuse note attachment.
5. **`seal(package, state, *, high_priority_cue_ids=None)`** (or `seal_observation_package`) — fail-closed gate rechecks, forces epistemic fields/disclaimer/version, captures `gate_state`, computes `package_hash`, sets `sealed=true`. **Sealed packages cannot be re-sealed or mutated via normal APIs** (`package_sealed` / `attach_officer_cue_notes` refusal).

## Repeated observation cycles (real-time pattern)

- Call `assert_can_observe(state)` before each cycle/run as needed.
- Produce unsealed package(s) with observations/cues; collect/merge context in your application layer if required (do not mutate a sealed package).
- Attach any `officer_cue_notes` to the final **unsealed** package.
- Seal once when the session/package is finalized.

## Errors

Stable `GateError.code` values: see `docs/GATE_ERROR_CODES.md`.
