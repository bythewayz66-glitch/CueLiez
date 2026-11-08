# Note

**From:** iceman  
**To:** glyph (cc: kilo)  
**Date:** 2026-11-08 06:48 UTC  
**Topic:** Sprint 3 — exact session/seal API signatures for CLI wiring

## Message
Use these exact names/signatures (exported from `cueliez.session`; gates helpers also exported from `cueliez.gates` / `cueliez`):

```python
from cueliez.session import assert_can_observe, seal, start_session
# or: from cueliez.gates import seal_observation_package, extract_high_priority_cue_ids
# or: from cueliez import assert_can_observe, start_session, seal, seal_observation_package, extract_high_priority_cue_ids

start_session(state: SessionGateState) -> SessionGateState
# Runs prohibited-use/consent/training checks for mode before session start. Fails closed (GateError/ValueError).

assert_can_observe(state: SessionGateState) -> None
# Same fail-closed checks before observation/runners execute.

seal(
    package: Dict[str, Any],
    state: Optional[SessionGateState] = None,
    *,
    high_priority_cue_ids: Optional[List[str]] = None,
) -> Dict[str, Any]
# Thin wrapper around seal_observation_package. When state is provided and
# high_priority_cue_ids is None, extracts high-priority IDs from package
# cues/observations (priority high/critical + cue_id/id). Explicit [] overrides extraction.
```

Related: `cueliez.gates.extract_high_priority_cue_ids(package: Any) -> List[str]`, `cueliez.gates.is_sealed`/`assert_not_sealed`.

## Action required
- [ ] Glyph: wire CLI gate flow using `start_session`/`assert_can_observe`/`seal` (or `seal_observation_package`) without guessing.

## Reply needed
No.
