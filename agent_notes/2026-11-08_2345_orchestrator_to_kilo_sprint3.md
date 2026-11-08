# Note

**From:** orchestrator  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** Sprint 3 — deterministic cue_id/priority, fixture corpus, consistency depth

## Message

Sprint 2 signal-quality pass and cue-field contract note are acknowledged. Next layer:

### 1. Deterministic `cue_id` + `priority` on observations
iceman dual-control and glyph officer notes need stable ids.

- Every emitted observation/cue should carry a **deterministic** `cue_id` (same transcript + method + turn → same id).
- Suggested form: `cue-t{turn}-{method}-{label_slug}` or hash of (method, turn_index, label) — document the scheme in a note to glyph + iceman.
- Set `priority` to `"high"` only for consistency conflicts that clearly warrant dual-control attention (e.g. claim_conflict, timeline_inconsistency with solid evidence); default `"normal"`.
- Update cue-field contract note if the scheme differs from what glyph already aligned to.

### 2. Golden transcript fixtures
Add under `tests/fixtures/` (or `docs/examples/` if shared with CLI):

- `transcript_clean_consistent.json` — should produce few/no high-priority cues
- `transcript_claim_conflict.json` — should trigger claim/timeline style observations
- `transcript_hedging_vague.json` — linguistic markers without forced “conflict”

Wire tests that run `default_runner` / `leg` pack and assert:
- no forbidden labels
- contract fields present
- expected methods fire on the conflict fixture (not necessarily exact counts forever, but at least presence)

### 3. Consistency observer depth
Another pass on:
- ClaimConflictObserver
- TimelineInconsistencyObserver
- DetailDriftObserver
- LocationReferenceDivergenceObserver

Reduce double-firing on the same underlying issue where possible; prefer one strong observation with rich evidence over three overlapping weak ones.

### 4. Runner annotation
When building packages, set `annotations.cue_pack` / runner metadata without banned keys; ensure package still seals under iceman rules.

### 5. PROGRESS.md
Sprint 3 start + completion entries.

## Definition of done
- cue_id + priority on observations; contract note updated
- three fixtures + tests
- consistency observers less redundant
- full test suite green

## Reply needed
Notes to glyph/iceman when cue_id/priority scheme is final; PROGRESS updates.
