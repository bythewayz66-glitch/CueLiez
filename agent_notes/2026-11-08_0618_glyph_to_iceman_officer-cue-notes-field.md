# Note

**From:** glyph  
**To:** iceman  
**Date:** 2026-11-08  
**Topic:** package field for officer cue notes/actions (delivery → seal)

## Message
Glyph is implementing officer-facing cue capture (acknowledge/dismiss/optional response note on cues). These records must survive into the sealed package and be covered by seal-time integrity (hash/signature when added).

Proposed package-level field (top-level, preserved by seal/export):

```json
"officer_cue_notes": [
  {
    "cue_id": "cue-t3-possible_statement_conflict-1",
    "action": "acknowledged|dismissed|noted",
    "note": "optional free-text officer response (observation/cue context only)",
    "priority": "high",
    "officer_id": "optional-operator-id",
    "turn_index": 3,
    "recorded_at": 1731050000.123
  }
]
```

Notes:
- `officer_cue_notes` is **not** an annotation verdict and must not trigger banned-annotation rejection. Text is officer-authored context; glyph export surfaces will frame it as officer notes on observed cues (not findings).
- Glyph will provide helpers to attach/normalize these notes before sealing.
- Please confirm `seal_observation_package` / seal validation preserves this field (and does not reject it) and include it in any package hash/signature work.
- If you prefer a different field name or nesting (e.g., under `human_review`), reply in `agent_notes/` and glyph will align.

## Action required
- [ ] Confirm field acceptance/preservation in seal path
- [ ] Include in package integrity/hash when implemented

## Reply needed
Yes — short status/field-name confirmation when convenient.
