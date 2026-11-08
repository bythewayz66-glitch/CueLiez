"""Consent-governed audio-feature observation hooks (Phase 2/7/8-ready, gated by default).

Consumes *derived* audio features/metadata only (no raw audio processing). Callers must
perform/ensure consent + jurisdiction checks before capture/extraction and before invoking hooks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .behavioral import ResponseLatencyObserver, SpeechRateShiftObserver
from .modality_gates import check_modality_allowed
from .prosody import PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver

AUDIO_FEATURE_OBSERVERS = (
    ResponseLatencyObserver(),
    SpeechRateShiftObserver(),
    PausePatternObserver(),
    ProsodicVariabilityObserver(),
    VoiceStressFeatureShiftObserver(),
)


def observe_audio_features(
    turns: Sequence[Mapping[str, Any]],
    *,
    state: Any = None,
    require_consent_check: bool = True,
) -> List[Dict[str, Any]]:
    """Run audio/latency/speech/pause/prosody feature observers on derived metadata turns.

    Consent-governed hook: when `require_consent_check` is True (default), enforces
    modality consent + jurisdiction via `check_modality_allowed(state, 'audio_features')`
    (canonical-aligned). Raises GateError if not allowed. Returns observation dicts.
    """
    if require_consent_check:
        if state is None:
            from ..gates import GateError
            raise GateError("gate_state_required", "Session gate state is required before enabling audio feature observation hooks.")
        check_modality_allowed(state, "audio_features")
    observations: List[Dict[str, Any]] = []
    for obs in AUDIO_FEATURE_OBSERVERS:
        observations.extend(obs.observe(turns).to_dicts())
    return observations
