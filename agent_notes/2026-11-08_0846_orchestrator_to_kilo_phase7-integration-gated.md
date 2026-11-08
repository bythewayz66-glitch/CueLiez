# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** Phase 7 — Integration & Gated Modalities (kilo scope)

## Message

Phase 7 kickoff. Your scope: gated modality observers and real-time audio path implementation, consent-governed, off by default.

### Tasks (in order)
1. **Physio/visual/wearable observers** — Keep gated; implement consent-governed enablement hooks only (no default enablement). Document.
2. **Real-time audio stream hooks** — Implement prosody, speech rate, latency, pause pattern observers behind explicit consent + jurisdiction checks (consent-governed).
3. **Consent/jurisdiction checks** — Implement and test checks before enabling audio feature extraction or camera/wearable input.
4. **Gated modality tests** — Add tests verifying observers remain off by default and require consent to enable.
5. **Docs** — Update `OBSERVER_INVENTORY.md` and gated modality docs; keep suite green.

### Constraints
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–5
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.