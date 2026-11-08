# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** Finish remaining work — kilo scope

## Message

Finish all remaining in-progress/open work. Your scope: ML/LLM-assisted observers, consent/jurisdiction checks, audio path, gated modality enablement, red-team transcript set, latency measurement, dependencies.

### Tasks (in order)
1. **Dependencies** — Add numpy/scipy only if used for signal features; otherwise document decision. Update `pyproject.toml` if added.
2. **ML/LLM-assisted observers** — Implement behind feature flags/model_id versioning for high-value signals; default off; document provenance. (Prototype exists; make it real.)
3. **Consent + jurisdiction checks** — Implement and test before enabling audio feature extraction or camera/wearable input.
4. **Audio-only real-time path** — Implement prosody, speech rate, latency, pause pattern observers (consent-governed).
5. **Gated modality enablement (Phase 8)** — Implement consent-governed enablement for physio/visual/wearable observers; keep off by default until policy-approved.
6. **Red-team transcript set** — Build private synthetic + de-identified transcript set for regression/utility testing; add tests.
7. **Latency measurement** — Measure and optimize end-to-end text cue latency (target <1–2s); document.
8. **Tests/docs** — Update `OBSERVER_INVENTORY.md`; keep suite green.

### Constraints
- No external ML in production path unless feature-flagged and documented.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–8
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.