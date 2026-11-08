"""Thin adapter for gated modality checks (aligned to canonical cueliez.gates APIs).

Canonical session APIs (iceman): record_modality_consent, require_gated_modality,
assert_can_observe(..., modalities=...). Gated input modalities: audio_features, camera, wearable.
This adapter maps observer-facing modality names and provides a stable helper; it delegates to
canonical checks for SessionGateState where possible and fails closed.
"""
from __future__ import annotations

from typing import Any

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
            if require_jurisdiction and not (mc.get("jurisdiction_approved") or state.get("jurisdiction_approved")):
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
