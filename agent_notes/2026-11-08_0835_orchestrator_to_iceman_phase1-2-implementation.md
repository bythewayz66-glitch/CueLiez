# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** IMPLEMENT Phase 1+2 — gates, consent/jurisdiction, session, schema

## Message

Implement Phase 1+2 now (owner demand). Your scope: gate hardening for real-time delivery, consent + jurisdiction checks, session lifecycle, schema stability, post-seal immutability.

### Tasks (in order)
1. **Consent + jurisdiction checks** — Implement explicit consent + jurisdiction validation before enabling audio feature extraction or camera/wearable input. Add `GateError` codes and tests.
2. **Session lifecycle for real-time** — Support repeated observation cycles and pre-seal officer note attach; document in `docs/SESSION_LIFECYCLE.md`. (Already partial; harden.)
3. **Schema stability** — If delivery adds fields (latency, cue provenance), version schema and update docs/tests. No breaking changes without note.
4. **Dual-control for high-priority cues** — Ensure government mode dual-control remains enforced for high-priority cues before seal; tests.
5. **Post-seal immutability** — Re-verify after changes; broaden if new mutation paths appear.
6. **Tests** — Add tests for new gate/consent/jurisdiction/session behavior; keep suite green.

### Constraints
- First-pilot modes only for messaging; government tested.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.