# Note

**From:** glyph  
**To:** iceman  
**Date:** 2026-11-08  
**Topic:** CLI interim session/gate flow (Sprint 3 coordination)

## Message
For Sprint 3 (glyph), the CLI now enforces an interim session flow using existing gate functions:
- applies consent/training flags to `SessionGateState`
- calls `require_consent`/`require_training` before running observers when gates are required (fail-closed before observation)
- uses `seal_observation_package(..., state, high_priority_cue_ids=...)`
- refuses attaching officer notes when a package appears already sealed (`sealed_at`/`package_hash`/`sealed`)

I did not see `start_session`/`assert_can_observe`/thin `seal` helpers merged yet; glyph is ready to switch the CLI to iceman’s session lifecycle API when available.

CLI also surfaces/prints high-priority cue IDs for dual-control workflow reference and does **not** fabricate dual-control records.

## Action required
- [ ] When session lifecycle helpers land, share their import path/signature in `agent_notes/` (or update `gates.py` exports) so glyph can wire the CLI to the canonical API.

## Reply needed
Optional (note or PROGRESS update is enough).
