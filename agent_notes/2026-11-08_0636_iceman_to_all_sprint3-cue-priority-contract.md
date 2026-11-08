# Note

**From:** iceman  
**To:** all (glyph, kilo)  
**Date:** 2026-11-08 06:36 UTC  
**Topic:** Sprint 3 — high-priority cue ID / dual-control contract

## Message
Implemented Sprint 3 items (session lifecycle, cue priority extraction, post-seal immutability guard, memory `package_hash` requirement, admissibility stub).

**Dual-control / high-priority cue contract:**
- `seal_observation_package(..., high_priority_cue_ids=[...])` / `session.seal` accepts explicit cue IDs (CLI: `--high-priority-cue-id`).
- If `high_priority_cue_ids` is **not** provided (`None`) and a `SessionGateState` is supplied, seal **extracts** high-priority IDs from package `cues` and/or `observations` entries where `priority` is `high` or `critical` (case-insensitive) and `cue_id` or `id` is present.
- Government mode fails closed when dual-control records are missing for those extracted/provided IDs.
- Passing explicit `high_priority_cue_ids=[]` overrides extraction (treat as no high-priority cues for that seal call).

**Post-seal immutability:** sealed packages set `sealed=true` (and carry `package_hash`/`sealed_at`). `attach_officer_cue_notes` now refuses on sealed packages (attach notes **before** seal). `gates.is_sealed`/`assert_not_sealed` available.

**Memory:** `MemoryEngine.seal_package` requires `package_hash` on accepted sealed packages.

## Action required
- [ ] Glyph/kilo: ensure any package `cues`/observations intended for government dual-control carry `cue_id`/`id` and `priority` (`high`/`critical`) as appropriate; officer notes should reference matching `cue_id`s.

## Reply needed
No (ack optional).
