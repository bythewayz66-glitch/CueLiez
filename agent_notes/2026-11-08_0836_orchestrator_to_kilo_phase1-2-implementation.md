# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** IMPLEMENT Phase 1+2 — observers, calibration, audio path, gated modalities

## Message

Implement Phase 1+2 now (owner demand). Your scope: production-grade observers, confidence calibration, insufficient-data states, gated modality implementation (consent-governed), audio-only real-time path. Keep rule-based baseline; no external ML in production unless feature-flagged.

### Tasks (in order)
1. **Confidence calibration** — Implement and document calibration/normalization for observer scores (heuristic but consistent); tests for bounds and stability.
2. **Insufficient data / no-cue states** — Implement explicit no-cue behavior across all observers for thin/empty/noisy input; tests.
3. **ML/LLM-assisted observers** — Implement behind feature flags/model_id versioning for high-value signals (hedging, pronoun distancing, detail vagueness, claim conflicts, timeline inconsistency). Default off. Document provenance.
4. **Gated modalities** — Implement consent + jurisdiction checks before enabling audio feature extraction or camera/wearable input; keep feature/physio/visual observers gated and off by default.
5. **Audio-only real-time path** — Implement prosody, speech rate, latency, pause pattern observers (consent-governed) as real code (not just design), gated by default.
6. **Latency** — Measure and optimize end-to-end text cue latency (target <1–2s); document.
7. **Tests/docs** — Update `OBSERVER_INVENTORY.md`; add tests; keep suite green.

### Constraints
- No external ML in production path unless feature-flagged and documented.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for contract/threshold changes.

## Action required
- [ ] Execute tasks 1–7
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.