# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** PHASE 0 CLOSEOUT — runner usability + dependency audit

## Message

Phase 0 closeout kickoff. Your scope: ensure default and full observation runners produce usable output on sample transcripts, and audit dependencies (add numpy/scipy only if actually used for signal features). Keep rule-based observers as baseline.

### Tasks (in order)
1. **Runner usability** — Verify `default_runner()` and `full_runner()` produce non-empty, contract-valid observations on `docs/examples/sample_transcript.json` and the three owner transcripts. Add a small smoke test (e.g., `tests/test_runner_phase0.py`) asserting runner output has observations with valid `cue_id`, `priority`, `confidence.score`, `model_id`, and no forbidden labels. `full_runner()` may emit nothing extra if feature metadata is absent — that is acceptable but must be documented.
2. **Insufficient-data clarity** — Ensure runners emit no cues (not errors) on very short/empty input; add a test.
3. **Dependency audit** — If you need numpy/scipy for signal features, add to `pyproject.toml` and import in code; otherwise leave deps as-is. Do not add unused dependencies. Post a note if you add any.
4. **Docs** — Update `docs/OBSERVER_INVENTORY.md` if runner behavior or thresholds change; keep first-pilot modes.

### Constraints
- Rule/heuristic baseline remains; no external ML in production path.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for dependency changes.

## Action required
- [ ] Execute tasks 1–4
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for dependency changes.