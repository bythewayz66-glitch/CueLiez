# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** HARDENING PASS — observer precision/coverage on owner transcripts

## Message

Hardening pass kickoff. Your scope: make observer output on the three owner transcripts match the intended quality bar, with wording treated as critical. Observer code and tests only; coordinate contract changes via notes.

Owner transcripts:
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

Current observed behavior:
- **clean:** false-positive hedging cue on "around nine-thirty" (the `\baround\b` pattern).
- **conflict:** no timeline/consistency cue because times are spelled out ("eight", "nine", "ten", "eight-thirty") and `TimelineInconsistencyObserver` only matches digit clock times.
- **hedging:** 8 cues; check density/dedup and that every cue wording stays neutral.

### Tasks (in order)

1. **Clean false positive** — Adjust hedging so ordinary time approximations ("around nine-thirty", "about six-fifteen") do not fire when they are the only hedge marker. Options: context-aware exclusion when the hedge token is immediately followed by a time expression, or require `count >= 2` (or `HEDGING_MIN_COUNT_OR_LONG` handling) for time-approximation tokens (`about`, `around`, `roughly`, `approximately`). Keep genuine hedges (e.g., "I guess", "maybe", "I don't remember") firing. Update `HEDGING_MIN_*` constants in `src/cueliez/observations/thresholds.py` if needed and document in `docs/OBSERVER_INVENTORY.md`.

2. **Spelled-out time handling** — Extend `TimelineInconsistencyObserver` (and thresholds) to recognize spelled-out hour/minute references common in transcripts ("eight", "nine", "ten", "eight-thirty", "nine-thirty", "eight o'clock"). Emit a neutral cue when multiple distinct time references appear across subject turns. Wording: "Multiple time references appear; verify the sequence and exact times." (neutral, no conflict assertion). Keep the existing note that multiple times may describe a sequence.

3. **Conflict transcript coverage** — Re-run on `owner_conflict_interview.json`; expect at least one timeline/consistency cue surfacing 8/9/10/8:30 with source quotes. If claim-conflict or detail-drift observers can be safely extended to catch the "whole time until ten" vs "gone by eight-thirty" contradiction without overclaiming, add it as a separate neutral cue; otherwise document the limitation in `OBSERVER_INVENTORY.md` and leave it. Do not assert deception.

4. **Hedging density review** — On `owner_hedging_interview.json`, review the 8 cues: remove duplicate/noise cues on the same turn where two observers fire on the same underlying phrase; keep distinct signals. If dedup is added, make it explainable in evidence.

5. **Golden regression tests** — Add `tests/test_hardening_owner_transcripts_kilo.py` (or extend `test_fixtures_golden.py`) asserting for each owner transcript:
   - clean: 0 cues (after task 1) — or document the single justified cue;
   - conflict: contains `timeline_inconsistency` (or the new method) with `source_texts` non-empty;
   - hedging: contains `hedging` cues, all `cue_id` deterministic, all `priority` in {normal, high}, no forbidden labels;
   - no forbidden verdict language in any cue/cue string.

6. **Language/wording audit** — Review all cue strings touched; ensure neutral, non-directive beyond "consider asking/probe/verify". Confirm `tests/test_language.py` still passes. Update `docs/OBSERVER_INVENTORY.md` for any threshold/observer change.

### Constraints
- Rule/heuristic only; no external ML in production path.
- Insufficient/thin data → no cue (do not invent weak cues).
- Do not enable feature/physio/visual observers by default.
- Keep deterministic `cue_id` and `priority` contract (v2).
- If method IDs or cue counts change, post an agent note before landing so glyph/iceman can adapt.

### Deliverables
- Code + tests committed.
- PROGRESS.md kilo section updated with counts.
- agent_note if contract (method ID, cue count, threshold semantics) changes.

## Action required
- [ ] Execute tasks 1–6 in order
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md (and note if contract changed)

## Reply needed
PROGRESS update; note for contract changes.