# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** LONG SPRINT — Phase 0 (deps) + 3.5 + Phase 4 + Phase 5 (kilo scope)

## Message

Long sprint kickoff. Your scope: Phase 0 dependency decision, Phase 3.5 internal validation notes (false-positive/over-cue rates), Phase 4 signal features gated, Phase 5 red-team transcript set.

### Tasks (in order)
1. **Phase 0 deps decision** — Add numpy/scipy only if actually used for signal features; otherwise leave deps empty. Document decision. Post a note if added.
2. **Phase 3.5 internal validation notes** — Prepare short notes on false-positive/over-cue rates and officer utility for the three owner transcripts (and sample), without claiming truth-detection accuracy. Store under `docs/` (e.g., `docs/validation/` or `docs/demo/`). Neutral wording.
3. **Phase 4: gated modalities** — Keep feature/physio/visual observers gated; do not enable by default. Document consent/jurisdiction checks needed before audio feature extraction or camera/wearable input. Prioritize audio-only real-time path (prosody, speech rate, latency, pause patterns) as design notes only.
4. **Phase 5: red-team transcript set** — Build private synthetic + de-identified transcript set for regression/utility testing (extend owner transcripts and fixtures). Add tests that run observers on them and report cue counts (no accuracy claims).
5. **Latency measurement** — Measure/estimate end-to-end latency for text cues on local instance; document (target <1–2s). No code change required unless a clear bottleneck.
6. **Tests** — Add tests for new red-team fixtures and gated-modality behavior; keep suite green.

### Constraints
- No external ML in production path.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Docs + tests committed by you.
- PROGRESS.md kilo section updated.
- agent_note for dependency/contract changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for dependency/contract changes.