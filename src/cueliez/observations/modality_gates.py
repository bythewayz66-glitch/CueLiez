"""Consent and jurisdiction checks for gated modalities (Phase 2 implementation).

Callers MUST perform these checks before enabling audio feature extraction or
camera/wearable-derived inputs, and before passing such features into observers.
Default runners do not include feature/physio/visual observers.
"""
from __future__ import annotations

from typing import Any

from ..gates import GateError, SessionGateState

SENSITIVE_MODALITIES = frozenset({"audio_features", "visual_features", "physiological_features"})
ALL_MODALITIES = frozenset({"text", *SENSITIVE_MODALITIES})


def _mode(state: Any) -> str:
    if isinstance(state, SessionGateState):
        return state.mode
    if isinstance(state, dict):
        return str(state.get("mode") or "generic")
    return str(getattr(state, "mode", "generic") or "generic")


def _consent_ok(state: Any) -> bool:
    if isinstance(state, SessionGateState):
        return state.consent_ok()
    if isinstance(state, dict):
        consent = bool(state.get("consent"))
        attester = str(state.get("consent_attested_by") or "").strip()
        recorded = state.get("consent_recorded_at")
        mode = str(state.get("mode") or "generic")
        from ..gates import CONSENT_REQUIRED_MODES
        if mode not in CONSENT_REQUIRED_MODES:
            return True
        return bool(consent and recorded and attester)
    return False


def _jurisdiction(state: Any) -> str:
    if isinstance(state, SessionGateState):
        return str(state.jurisdiction or "").strip()
    if isinstance(state, dict):
        return str(state.get("jurisdiction") or "").strip()
    return str(getattr(state, "jurisdiction", "") or "").strip()


def check_modality_allowed(
    state: Any,
    modality: str,
    *,
    action: str = "enable modality",
    require_jurisdiction: bool = True,
) -> None:
    """Fail-closed consent + jurisdiction checks for gated modalities.

    - text: allowed (subject to normal session gates handled elsewhere).
    - audio_features / visual_features / physiological_features: require recorded consent
      when mode requires it, and require a non-empty jurisdiction record when
      `require_jurisdiction` is True (jurisdiction/policy must be identified before
      capture/extraction of sensitive modalities).
    """
    mod = str(modality or "").strip().lower()
    if mod not in ALL_MODALITIES:
        raise GateError("modality_invalid", f"Unknown modality {modality!r}.")
    if mod == "text":
        return
    if not _consent_ok(state):
        raise GateError(
            "modality_consent_required",
            f"Recorded consent with attester is required before {action} ({mod}, mode={_mode(state)!r}).",
        )
    if require_jurisdiction and not _jurisdiction(state):
        raise GateError(
            "modality_jurisdiction_required",
            f"Jurisdiction must be recorded before {action} ({mod}, mode={_mode(state)!r}).",
        )


def modality_observers_allowed(state: Any, modality: str) -> bool:
    try:
        check_modality_allowed(state, modality)
        return True
    except GateError:
        return False
