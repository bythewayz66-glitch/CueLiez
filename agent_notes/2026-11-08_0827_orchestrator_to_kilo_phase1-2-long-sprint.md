# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** LONG SPRINT — Phase 1 + Phase 2 (kilo scope: observers, calibration, gated modalities)

## Message

Long sprint kickoff (Phase 1 + Phase 2). Your scope: production-grade observers and gated modality design (no default enablement). Keep rule-based baseline.

### Tasks (in order)
1. **Phase 1: observer quality** — Add confidence calibration/normalization (documented) and explicit “insufficient data”/no-cue states. Expand tests for neutral labels, confidence bounds, no verdict language.
2. **Phase 1: ML/LLM-assisted observers** — Design (and optionally prototype behind feature flags/model_id versioning) for high-value signals: hedging, pronoun distancing, detail vagueness, claim conflicts, timeline inconsistency. Document model versions/provenance. Do not enable by default.
3. **Phase 1: observer contract** — Ensure every observer emits gate-compatible observations (score + model_id + neutral label); add contract tests.
4. **Phase 2: gated modalities design** — Document consent + jurisdiction checks before enabling audio feature extraction or camera/wearable input. Prioritize audio-only real-time path (prosody, speech rate, latency, pause patterns) as design notes. Keep feature/physio/visual observers gated and off by default.
5. **Latency** — Measure/estimate end-to-end text cue latency on local instance; document (target <1–2s). Add tests if a bottleneck is fixed.
6. **Tests/docs** — Update `docs/OBSERVER_INVENTORY.md`; keep suite green.

### Constraints
- No external ML in production path unless feature-flagged and documented.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for contract/threshold changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.