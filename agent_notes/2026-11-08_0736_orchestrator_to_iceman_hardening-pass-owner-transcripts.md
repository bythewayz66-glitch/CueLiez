# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** HARDENING PASS — seal/gate/hash integrity for owner transcripts

## Message

Hardening pass kickoff. Your scope: prove the seal/gate/hash/evidence path is solid on the three owner demo transcripts, with wording and epistemic fields correct. No schema expansion beyond current v1 unless a test exposes a real gap; if so, note it first.

Owner transcripts:
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

### Tasks (in order)

1. **Seal-path regression tests** — Add `tests/test_hardening_owner_transcripts_iceman.py` (or extend `test_e2e_matrix.py`) that, for each transcript:
   - runs the default observation runner,
   - seals via `seal_observation_package` (generic mode, no consent required) and via the session helper path where applicable,
   - asserts `epistemic_status == "observed_indicator"`, `is_definitive_finding is False`, `origin == "grounded"`, `product == "CueLiez"`, non-empty canonical disclaimer, `schema_version`, `product_version`, `sealed_at`, `package_hash`.
2. **Evidence preservation** — Assert observation evidence dicts (including `source_text`/`source_texts` and role/turn refs) are present in the sealed package for every observation; no stripping of unknown evidence keys.
3. **Hash reproducibility** — Assert `verify_package_hash` passes for each sealed package and that recomputing the hash yields the same value (deterministic inputs).
4. **Post-seal immutability** — Assert `is_sealed` is true and `attach_officer_cue_notes` (and any observation mutation) is refused after seal for each package.
5. **Banned-content rejection** — Negative tests: seal-time rejection of observations/annotations using verdict language or banned keys (`lying`, `deception_confirmed`, `guilty`, `diagnosis`, `truth_score`, etc.) for all three transcript-derived packages.
6. **Gate state capture** — Assert full `gate_state` is serialized (mode, consent fields, training, dual-control list, intended uses, requirements) even in generic mode (nulls allowed, structure required).
7. **Memory substrate** — Assert `MemoryEngine.seal_package` requires `package_hash` and stored seals keep `observed_indicator`/non-finding status (existing L8 behavior) for these packages.
8. **Wording check** — Confirm no forbidden terms in any new test names/strings or doc additions; keep cue/label wording neutral. Update `docs/ADMISSIBILITY_AND_DISCLOSURE.md` only if a real gap appears (do not strengthen claims).

### Constraints
- First-pilot modes only (`generic`, `interrogation`); government tested but not pilot messaging.
- No new modalities enabled by default.
- Do not weaken existing tests; if kilo's changes alter cue counts, update expectations via agent note, not by loosening assertions.
- Run full suite before reporting; target remains green.

### Deliverables
- New/updated tests committed.
- PROGRESS.md iceman section updated.
- agent_note only if a contract (field name, hash input, gate code) changes.

## Action required
- [ ] Execute tasks 1–8 in order
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note only for contract changes.