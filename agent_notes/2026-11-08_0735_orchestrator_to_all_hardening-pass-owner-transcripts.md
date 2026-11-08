# Note

**From:** orchestrator
**To:** all
**Date:** 2026-11-08
**Topic:** HARDENING PASS — owner demo transcripts (wording is critical)

## Message

Next natural step after the completed long sprint and locked owner decisions: a **hardening pass** driven by the three synthetic owner demo transcripts. These are the reference quality bar for the first pilot (`generic` + `interrogation` only).

Owner transcripts (fully synthetic; see `docs/OWNER_DECISIONS.md` §4):
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

Baseline at kickoff: full suite green (**260 tests, 1 skipped**), git clean on `main`, remote `bythewayz66-glitch/CueLiez`.

Observed current behavior on these transcripts (run `python -m cueliez <file> --mode generic --show-cues`):
- **clean:** 1 cue — false-positive hedging on "around nine-thirty" (ordinary time approximation).
- **conflict:** 2 cues (hedging/vagueness on one turn) but **no** timeline/consistency cue, because the contradictory times are spelled out ("eight", "nine", "ten", "eight-thirty") and the timeline observer only matches digit clock times.
- **hedging:** 8 cues; wording is neutral but density and any over-cueing must be reviewed.

### Wording is critical
Every cue string, CLI line, export heading, and doc sentence must obey `AGENTS.md`, `docs/LANGUAGE_RULES.md`, and the locked never-claim paragraph in `docs/OWNER_DECISIONS.md` §1. No verdict or banned language (see `AGENTS.md` §§1–2). "Wording is critical" applies to code comments and tests too. If a wording change is needed, note it in `agent_notes/` before landing.

### Hardening success criteria (team)
1. **Clean** transcript produces **0 cues** (or at most 1 clearly-justified low-score cue) and seals cleanly.
2. **Conflict** transcript produces at least one neutral timeline/consistency cue that surfaces the contradictory time references, with source quotes.
3. **Hedging** transcript keeps useful hedging/vagueness cues but avoids duplicate/noise cues on the same turn where possible; all wording neutral.
4. All three transcripts seal with correct epistemic fields, gate state, package hash, and preserved source evidence.
5. Full suite green; new regression tests reference the three transcripts; PROGRESS current.
6. No scope expansion beyond first-pilot modes (`generic`, `interrogation`); no new modalities enabled by default.

### Coordination
- kilo owns observer precision/coverage changes and threshold tuning; post a note if cue counts or method IDs change.
- iceman owns seal/gate/hash/evidence integrity tests for these transcripts.
- glyph owns CLI/export/demo wording and dry-run paths.
- Use `agent_notes/` for any contract change; keep notes tight.

## Action required
- [ ] Read your individual hardening note
- [ ] Execute in order; update PROGRESS.md per major item
- [ ] Reply via agent_notes if a contract changes

## Reply needed
Status updates in PROGRESS.md; notes only for contract changes.