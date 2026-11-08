# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** PHASE 3 — observer quality, calibration, insufficient-data states

## Message

Phase 3 (Admissibility Hardening) kickoff. Your scope: observer quality and admissibility-facing observation contract. Keep rule/heuristic baseline; no external ML in production path.

### Tasks (in order)
1. **Language audit (observer surface)** — Audit all observer labels/cue strings/evidence keys for forbidden terms; ensure neutral wording. Extend `test_language.py` coverage if needed.
2. **Confidence calibration** — Document and (if cheap) apply simple calibration/normalization for observer scores; keep score in [0,1]. Add tests for bounds.
3. **Insufficient data / no-cue states** — Ensure thin/empty input yields no observations (not errors) across all observers; add tests for empty/single-turn/noise inputs.
4. **Neutral labels** — Verify every observation has neutral `label`, `confidence.score`, non-empty `model_id`, `method`, `category`, `evidence`. Add a contract test (already partially in `test_observations_base.py`; expand).
5. **Reproducibility** — Ensure deterministic `cue_id` and stable output under same input/model versions; add a test.
6. **Docs** — Update `docs/OBSERVER_INVENTORY.md` for any threshold/calibration changes.

### Constraints
- No external ML in production path.
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