# Note

**From:** orchestrator  
**To:** all  
**Date:** 2026-11-08  
**Topic:** Owner decisions locked + preferred demo transcripts

## Message

Read and obey:

**`docs/OWNER_DECISIONS.md`**

Highlights:
- **Never-claim paragraph** is locked for all user-facing text.
- **First pilot modes:** `generic` + `interrogation` only (government implemented but not first external pilot).
- Clinical/therapy messaging and physio/visual modalities stay out of pilot scope.
- Deploy posture: on-prem / private-cloud first; no live Axon/RMS integration required this sprint.

Preferred owner demo transcripts (synthetic):
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

### Agent actions
- **glyph:** Point `OPERATOR_DRY_RUN.md` at these three as preferred demos; run CLI dry paths against them when convenient.
- **kilo:** Optional golden-style checks against these files is welcome but not mandatory if fixtures already cover the space.
- **iceman:** No schema change required; ensure any new docs/examples language stays non-finding.

Admissibility guide v1 is **owner-accepted** as directionally correct—do not strengthen claims beyond it.

Long sprint remains active for any unfinished L-items; otherwise hold for orchestrator review / next hardening pass.

## Reply needed
One-line PROGRESS acknowledgment that OWNER_DECISIONS was read.
