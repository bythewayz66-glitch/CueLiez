"""Session lifecycle helpers for gated observation/seal flows.

Iceman-owned: ensures high-stakes modes cannot observe or seal without required gates.
Glyph CLI and future UIs should use this path for a clear fail-closed lifecycle.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .gates import (
    SessionGateState,
    check_prohibited_uses,
    extract_high_priority_cue_ids,
    require_consent,
    require_dual_control_for_seal,
    require_gated_modality,
    require_training,
    seal_observation_package,
)


def start_session(state: SessionGateState) -> SessionGateState:
    """Validate that a session may start. Fails closed if required gates are not ready."""
    if state is None:
        raise ValueError("state is required")
    check_prohibited_uses(state.intended_uses)
    require_consent(state, action="start")
    require_training(state)
    return state


def assert_can_observe(state: SessionGateState, modalities: Optional[list[str]] = None) -> None:
    """Assert observation/runners may execute for this session. Fails closed.

    When modalities are provided (e.g. audio_features, camera, wearable), explicit
    consent + jurisdiction validation is required for each gated input modality.
    Safe to call repeatedly (real-time observation cycles).
    """
    if state is None:
        raise ValueError("state is required")
    check_prohibited_uses(state.intended_uses)
    require_consent(state, action="observe")
    require_training(state)
    for mod in (modalities or []):
        require_gated_modality(state, mod)


def seal(
    package: Dict[str, Any],
    state: Optional[SessionGateState] = None,
    *,
    high_priority_cue_ids: Optional[List[str]] = None,
    signer: Any = None,
) -> Dict[str, Any]:
    """Seal an observation package through the gate-hardened seal path."""
    return seal_observation_package(package, state, high_priority_cue_ids=high_priority_cue_ids, signer=signer)


__all__ = [
    "SessionGateState",
    "assert_can_observe",
    "extract_high_priority_cue_ids",
    "seal",
    "seal_observation_package",
    "start_session",
]
