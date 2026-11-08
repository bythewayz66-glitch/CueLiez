# Note

**From:** orchestrator  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** LONG SPRINT — observers, fixtures, cue identity, pack maturity

## Status
Sprint 2 signal-quality work is in. Finish any open Sprint 3 items (cue_id/priority, fixtures), then continue this list without stopping.

Work **top to bottom**. PROGRESS after each major item.

---

### L1 — Deterministic `cue_id` + `priority` (if not already done)
- Every observation gets stable `cue_id` and `priority` (`normal`|`high`)
- Document scheme in note to iceman + glyph
- High only for strong consistency conflicts with solid evidence

### L2 — Golden fixture corpus
Under `tests/fixtures/transcripts/` (create if needed):

| File | Intent |
|------|--------|
| `clean_consistent.json` | Minimal/no high-priority |
| `claim_conflict.json` | claim/timeline conflict fires |
| `hedging_vague.json` | linguistic markers, not forced conflict |
| `evasion_short.json` | behavioral evasion / short answers |
| `multi_turn_drift.json` | detail drift across turns |

Tests: runner + leg pack; contract fields; expected method families present/absent as appropriate; **zero** forbidden labels.

### L3 — Consistency de-duplication
Claim / timeline / detail-drift / location observers: reduce overlapping weak cues; prefer one strong evidenced observation.

### L4 — Explicit insufficient-data path
Document and test: empty transcript, single token, null turns → **no** observations (not low-confidence noise).

### L5 — Observer registry / inventory
`docs/OBSERVER_INVENTORY.md`:
- method id, category, rule vs future-ML, default pack membership, model_id pattern
- which are off-by-default (feature/physio/visual)

### L6 — Pack review
- `leg`, `gov`, `med`, `thrp`: guidance text language-clean
- defaults remain text-only
- gov pack documents dual-control expectation for high-priority (process note, not enforcement — iceman enforces)

### L7 — Calibration hooks (lightweight)
- Optional per-observer min evidence thresholds constants in one place
- No external ML required
- Tests still pass with defaults

### L8 — Optional test-only Pollinations probe
- Behind clearly named test helper or `tests/` only
- Must not import into production observer path
- Skip-friendly if network blocked

### L9 — Regression suite target
- Fixture corpus + unit tests for all high-value observers
- Full suite green after each merge

### L10 — Ongoing
Respond to iceman priority-contract and glyph renderer notes; keep cue contract stable once published.

## Out of scope
Seal/hash implementation, officer UI, PDF marketing.

## Long-sprint done when
Stable cue_id/priority; ≥5 fixtures with tests; inventory doc; packs audited; consistency quieter; suite green.
