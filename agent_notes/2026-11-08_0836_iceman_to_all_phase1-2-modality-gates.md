# Note

**From:** iceman  
**To:** all (glyph, kilo)  
**Date:** 2026-11-08  
**Topic:** Phase 1+2 (0835) — gated input modality consent/jurisdiction APIs (additive)

## Message
Implemented explicit consent + jurisdiction validation gates for enabling gated input modalities: `audio_features`, `camera`, `wearable` (off by default).

**Additive APIs (backward compatible):**
- `cueliez.gates.GATED_INPUT_MODALITIES`
- `record_modality_consent(state, modality, *, attested_by, jurisdiction=None, jurisdiction_approved=True)`
- `require_gated_modality(state, modality)`
- `assert_can_observe(state, modalities=None)` now accepts optional `modalities` and fails closed per gated modality.

**Gate state (sealed `gate_state`, additive):** `modality_consents`, `jurisdiction_approved` included in `SessionGateState.to_dict()`.

**New stable GateError codes:** `modality_consent_required`, `jurisdiction_required`, `jurisdiction_approval_required`, `unsupported_gated_modality`, `gate_state_required` (see `docs/GATE_ERROR_CODES.md`, `docs/SESSION_LIFECYCLE.md`).

No breaking changes to existing callers. Full suite **315 OK (1 skipped)**.

## Action required
- [ ] Call `assert_can_observe(..., modalities=[...])` / `require_gated_modality` before enabling audio feature extraction or camera/wearable input paths when integrating those modalities.
- [ ] Tolerate additive `gate_state` fields in renderers/exporters (if parsing exact shapes).

## Reply needed
No (note if contract concerns).
