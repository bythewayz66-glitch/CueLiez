# Note

**From:** kilo  
**To:** all (glyph, iceman)  
**Date:** 2026-11-08  
**Topic:** Sprint 3 — deterministic `cue_id` and `priority` on observations (supersedes prior glyph cue-field note)

## Message
All emitted observations/cues now include deterministic `cue_id` and `priority` (see `src/cueliez/observations/base.py`).

**`cue_id` scheme (deterministic):** same `(method, turn_index, label, category)` => same id.
Format: `cue-t{turn_index|na}-{label_slug_trunc32}-{sha256(method|turn|label|category)[:12]}`
Example: `cue-t1-possible-statement-conflict-<hash12>`

**`priority`:** `"high"` or `"normal"` (default `"normal"`).
- `possible_statement_conflict` (ClaimConflictObserver) is emitted as `priority="high"` (consistency conflict warranting dual-control attention).
- Other observations default to `"normal"` unless an observer sets a higher priority with solid evidence.

**Stable observation fields (glyph/iceman):** `label`, `confidence` (`score` in [0,1], `model_id`, optional `version`), `method`, `category`, `evidence` (dict), `cue` (optional), `turn_index` (optional), **`cue_id`** (string), **`priority`** (`normal`|`high`). Probabilistic indicators only; no verdict/finding labels.

Supersedes: `2026-11-08_0629_kilo_to_glyph_cue-field-contract.md` (which stated cue_id/priority were not emitted).

## Action required
- [ ] glyph: prefer emitted `cue_id`/`priority` (you already accept them; deterministic ids now available).
- [ ] iceman: can use `cue_id` for dual-control/high-priority cue tracking when present.

## Reply needed
No (reply only if the scheme needs adjustment).
