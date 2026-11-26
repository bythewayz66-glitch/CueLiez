"""Thin adapter for gated modality checks (aligned to canonical cueliez.gates APIs).

Canonical session APIs (iceman): record_modality_consent, require_gated_modality,
assert_can_observe(..., modalities=...). Gated input modalities: audio_features, camera, wearable.
This adapter maps observer-facing modality names and provides a stable helper; it delegates to
canonical checks for SessionGateState where possible and fails closed.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..gates import (
    GATED_INPUT_MODALITIES,
    GateError,
    SessionGateState,
    record_modality_consent,
    require_gated_modality,
)

# Observer-facing aliases -> canonical gated input modalities.
MODALITY_ALIASES = {
    "audio_features": "audio_features",
    "audio": "audio_features",
    "visual_features": "camera",
    "camera": "camera",
    "video": "camera",
    "physiological_features": "wearable",
    "physiological": "wearable",
    "physio": "wearable",
    "wearable": "wearable",
}
ALL_MODALITIES = frozenset({"text", *MODALITY_ALIASES.keys()})


def canonical_modality(modality: str) -> str | None:
    key = (modality or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key == "text":
        return "text"
    return MODALITY_ALIASES.get(key)


def check_modality_allowed(
    state: Any,
    modality: str,
    *,
    action: str = "enable modality",
    require_jurisdiction: bool = True,
) -> None:
    """Fail-closed consent + jurisdiction checks for gated modalities (canonical-aligned).

    Uses cueliez.gates.require_gated_modality for SessionGateState when applicable.
    Requires explicit per-modality consent records for gated inputs (audio_features/camera/wearable).
    """
    canon = canonical_modality(modality)
    if canon is None:
        raise GateError("modality_invalid", f"Unknown modality {modality!r}.")
    if canon == "text":
        return
    if isinstance(state, SessionGateState):
        if canon in GATED_INPUT_MODALITIES:
            require_gated_modality(state, canon)
            return
    # Dict/compat fallback: require base consent+jx and treat as needing explicit modality handling.
    # Fail closed with canonical-style codes.
    if isinstance(state, dict):
        consent = bool(state.get("consent"))
        attester = str(state.get("consent_attested_by") or "").strip()
        recorded = state.get("consent_recorded_at")
        mode = str(state.get("mode") or "generic")
        from ..gates import CONSENT_REQUIRED_MODES
        if mode in CONSENT_REQUIRED_MODES and not (consent and recorded and attester):
            raise GateError("modality_consent_required", f"Explicit consent is required before enabling gated input modality {canon!r}.")
        mc = (state.get("modality_consents") or {}).get(canon)
        if mc and mc.get("consented") and str(mc.get("attested_by") or attester).strip():
            jur = str(mc.get("jurisdiction") or state.get("jurisdiction") or "").strip()
            if require_jurisdiction and not jur:
                raise GateError("jurisdiction_required", f"Jurisdiction must be recorded before enabling gated input modality {canon!r}.")
            # Per-modality approval ONLY: a state-wide jurisdiction_approved
            # flag must never satisfy a per-modality check (owner decision,
            # Track A fix, 2026-11-25).
            if require_jurisdiction and not mc.get("jurisdiction_approved"):
                raise GateError("jurisdiction_approval_required", f"Jurisdiction approval is required before enabling gated input modality {canon!r}.")
            return
        # No per-modality record: fail closed (canonical requires explicit modality consent).
        raise GateError("modality_consent_required", f"Explicit consent is required before enabling gated input modality {canon!r}.")
    raise GateError("gate_state_required", f"Session gate state is required before {action} ({canon}).")


def modality_observers_allowed(state: Any, modality: str) -> bool:
    try:
        check_modality_allowed(state, modality)
        return True
    except GateError:
        return False


# ---------------------------------------------------------------------------
# Demographic inference: SEPARATE gate (owner decision, 2026-11-25 20:00 MST).
#
# Demographic inference is NOT covered by the general modality gate
# (audio_features / camera / wearable) and must never be treated as
# enabled by camera consent, jurisdiction approval, or any other
# modality consent. It requires its OWN separate opt-in and its OWN
# separate consent record, because it is high-risk, bias-prone and
# admissibility-sensitive.
#
# Expected record shape (canonical, Track A, ``cueliez.gates``):
#
#   SessionGateState.demographic_inference_consent = {
#       "consented": True, "attested_by": "<officer id>",
#       "jurisdiction": "<jurisdiction>", "jurisdiction_approved": True,
#       "recorded_at": <epoch seconds>,
#   }
#
# written by ``record_demographic_inference_consent`` and checked by
# ``require_demographic_inference_consent`` (which looks ONLY at that
# record — never modality_consents, never the state-wide
# jurisdiction_approved flag). Revocation touches only this record.
# Camera consent, audio consent, wearable consent, or a state-wide
# jurisdiction approval alone NEVER satisfy this check.
# ---------------------------------------------------------------------------

DEMOGRAPHIC_INFERENCE_GATE = "demographic_inference"


def _demographic_record(state: Any) -> Optional[Mapping[str, Any]]:
    """Return the separate demographic-inference consent record, if any."""
    if isinstance(state, SessionGateState):
        # Canonical record is the separate attribute (Track A).
        rec = getattr(state, "demographic_inference_consent", None)
        if isinstance(rec, Mapping):
            return rec
        recs = getattr(state, "modality_consents", None)
        if isinstance(recs, Mapping):
            rec = recs.get(DEMOGRAPHIC_INFERENCE_GATE)
            if isinstance(rec, Mapping):
                return rec
        return None
    if isinstance(state, Mapping):
        rec = state.get("demographic_inference_consent")
        if isinstance(rec, Mapping):
            return rec
        recs = state.get("modality_consents")
        if isinstance(recs, Mapping):
            rec = recs.get(DEMOGRAPHIC_INFERENCE_GATE)
            if isinstance(rec, Mapping):
                return rec
    return None


def check_demographic_inference_allowed(state: Any, *, require_jurisdiction: bool = True) -> None:
    """Fail-closed check for the SEPARATE demographic-inference gate.

    Delegates to canonical ``cueliez.gates.require_demographic_inference_consent``
    for SessionGateState (which checks ONLY the separate record).
    Raises GateError unless a dedicated demographic-inference consent
    record exists with consented=True, a non-empty attester, and (when
    required) jurisdiction + jurisdiction approval. General modality
    consent (camera/audio/wearable) is explicitly NOT sufficient.
    """
    if isinstance(state, SessionGateState):
        from ..gates import require_demographic_inference_consent

        require_demographic_inference_consent(state)
        return
    rec = _demographic_record(state)
    if rec is None:
        raise GateError(
            "demographic_inference_consent_required",
            "Demographic inference requires its own separate opt-in and consent "
            "record ('demographic_inference'); general modality consent is not sufficient.",
        )
    if not rec.get("consented"):
        raise GateError(
            "demographic_inference_consent_required",
            "Demographic inference consent record exists but is not consented.",
        )
    if not str(rec.get("attested_by") or "").strip():
        raise GateError(
            "demographic_inference_consent_required",
            "Demographic inference consent record has no attester.",
        )
    if require_jurisdiction:
        if not str(rec.get("jurisdiction") or "").strip():
            raise GateError(
                "demographic_inference_jurisdiction_required",
                "Jurisdiction must be recorded for demographic inference.",
            )
        if not rec.get("jurisdiction_approved"):
            raise GateError(
                "demographic_inference_jurisdiction_approval_required",
                "Jurisdiction approval is required for demographic inference.",
            )


def demographic_inference_allowed(state: Any) -> bool:
    try:
        check_demographic_inference_allowed(state)
        return True
    except GateError:
        return False
