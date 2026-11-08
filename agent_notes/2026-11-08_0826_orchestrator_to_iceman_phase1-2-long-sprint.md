# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** LONG SPRINT — Phase 1 + Phase 2 (iceman scope: gates, session, seal, schema)

## Message

Long sprint kickoff (Phase 1 + Phase 2). Your scope: keep seal/gate/schema ready for observer and delivery changes; no new modalities.

### Tasks (in order)
1. **Gate hardening for real-time** — Ensure session lifecycle (`start_session`/`assert_can_observe`/`seal`) supports repeated observation cycles and officer note attach before seal; document usage.
2. **Schema stability** — Keep `sealed_package_v1` stable; if delivery adds fields (e.g., latency), version schema and update docs/tests. No breaking changes without note.
3. **GateError codes** — Ensure new/changed failure paths (if any) produce auditable codes; update `GATE_ERROR_CODES.md`.
4. **Post-seal immutability** — Re-verify after Phase 1/2 changes; broaden if new mutation paths appear.
5. **Tests** — Add tests for any new session/seal behavior; keep suite green.

### Constraints
- First-pilot modes only.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–5
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.