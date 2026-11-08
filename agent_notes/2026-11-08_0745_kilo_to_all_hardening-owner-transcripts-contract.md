# Note

**From:** kilo  
**To:** all (glyph, iceman)  
**Date:** 2026-11-08  
**Topic:** Hardening pass (owner transcripts) — observer behavior/cue-count changes

## Message
Implemented 0737 hardening pass (observer precision/coverage) for `docs/examples/owner_clean_interview.json`, `owner_conflict_interview.json`, `owner_hedging_interview.json`. No method IDs or `cue_id`/`priority`/evidence contract fields changed. Labels/method IDs unchanged.

**Behavior changes (cue counts may differ):**
- `cueliez.observations.linguistic.hedging/v1`: excludes time-approximation tokens (`about`/`around`/`roughly`/`approximately`) when immediately followed by a clock-time expression (e.g., "around nine-thirty", "about 6:15") so ordinary time approximations do not fire as sole hedges. Genuine hedges (e.g., "maybe", "I guess", "I don't remember") still fire. Uses `HEDGING_*` thresholds from `observations/thresholds.py`.
- `cueliez.observations.consistency.timeline_inconsistency/v1`: recognizes spelled-out hour/minute references in time-context (e.g., "at eight", "nine-thirty", "eight o'clock") in addition to digit clock times. Emits the same neutral label/cue: `multiple_time_references_present` / "Multiple specific time references appear across responses; verify the sequence and exact times." Evidence still includes `source_texts`/turn refs; note remains that multiple times may describe a sequence (not a conflict assertion).

**Owner transcript baseline (post-hardening, default runner/generic CLI):**
- `owner_clean_interview.json`: 0 cues.
- `owner_conflict_interview.json`: 2 cues (vagueness on T5; timeline/multiple_time_references_present surfacing spelled-out refs 8/9/10/8:30 with source quotes). Hedging on T5 no longer fires (only "maybe" remains after time-approx exclusion + short-text precision guard). Claim/detail-drift observers do not assert the "until ten" vs "gone by eight-thirty" contradiction as a safe conflict; limitation to be noted in inventory if kept.
- `owner_hedging_interview.json`: 8 cues (hedging/vagueness; distinct signals reviewed; T3/T11 have hedging+vagueness on different underlying phrases, kept).

## Action required
- [ ] glyph/iceman: if any golden/demo expectations pin exact cue counts/IDs for these transcripts, update to post-hardening baseline. `cue_id` deterministic scheme unchanged.
- [ ] iceman: seal/evidence integrity unaffected (evidence keys preserved).

## Reply needed
No (PROGRESS/coordination as needed).
