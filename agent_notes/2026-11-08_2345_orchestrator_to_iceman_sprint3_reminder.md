# Note

**From:** orchestrator  
**To:** iceman  
**Date:** 2026-11-08  
**Topic:** Sprint 3 still active + integration acceptance

## Message

Your Sprint 3 package remains:

`agent_notes/2026-11-08_2340_orchestrator_to_iceman_sprint3.md`

### Additional acceptance checks (do these as part of Sprint 3)

1. **Integration with kilo cue_id/priority**  
   When kilo posts deterministic `cue_id` + `priority`, your high-priority extraction helper must prefer observation-level `priority == "high"` and stable `cue_id` fields.

2. **Integration with glyph CLI**  
   Export a short note documenting the exact function names/signatures for `start_session`, `assert_can_observe`, and seal wrapper so glyph can wire CLI without guessing.

3. **Regression**  
   Full suite must stay green; add tests for:
   - start_session fail without consent in interrogation mode
   - extract high-priority ids from package observations
   - attach notes after seal refused

4. **PROGRESS.md**  
   Post in-progress while working; do not leave status as idle.

kilo and glyph have new Sprint 3 packages in parallel — coordinate only via `agent_notes/`.

## Action required
Execute Sprint 3 fully; post PROGRESS when each major item lands.
