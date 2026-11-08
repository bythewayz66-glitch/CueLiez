"""Run observation methods and build gate-compatible packages."""

from __future__ import annotations

from collections.abc import Mapping as AbcMapping, Sequence as AbcSequence
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .base import ObservationResult, Observer
from .behavioral import (
    AnswerLengthVarianceObserver,
    EvasionMarkerObserver,
    FilledPauseMarkerObserver,
    InterruptionOverlapObserver,
    ResponseLatencyObserver,
    SpeechRateShiftObserver,
)
from .consistency import (
    ClaimConflictObserver,
    DetailDriftObserver,
    LocationReferenceDivergenceObserver,
    SelfReferenceShiftObserver,
    TimelineInconsistencyObserver,
)
from .linguistic import (
    CertaintySwingObserver,
    DetailVaguenessObserver,
    HedgingObserver,
    MemoryQualifierObserver,
    MinimizationObserver,
    NegationDensityObserver,
    OverjustificationObserver,
    PassiveVoiceProxyObserver,
    PronounDistancingObserver,
)
from .multimodal import add_convergence_observations
from .physiological import ElectrodermalShiftObserver, HeartRateShiftObserver, HrvShiftObserver
from .prosody import PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver
from .visual import BlinkRateObserver, GazePatternObserver, MotorActivityObserver


def _normalize_transcript(transcript: Any) -> Sequence[Any]:
    """Accept a turn sequence or a wrapper object with 'turns'/'transcript'."""
    if isinstance(transcript, AbcMapping):
        for key in ("turns", "transcript", "messages"):
            v = transcript.get(key)
            if isinstance(v, AbcSequence) and not isinstance(v, (str, bytes)):
                return v
        return []
    if transcript is None:
        return []
    return transcript


class ObservationRunner:
    def __init__(self, observers: Optional[Sequence[Observer]] = None):
        self.observers: List[Observer] = list(observers) if observers is not None else []

    def run(self, transcript: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        turns = _normalize_transcript(transcript)
        observations: List[Dict[str, Any]] = []
        for obs in self.observers:
            res: ObservationResult = obs.observe(turns)
            observations.extend(res.to_dicts())
        return observations

    def build_package(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        session_id: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        include_convergence: bool = True,
        min_convergence_categories: int = 2,
    ) -> Dict[str, Any]:
        observations = self.run(transcript)
        if include_convergence:
            observations = add_convergence_observations(observations, min_categories=min_convergence_categories)
        package: Dict[str, Any] = {
            "observations": observations,
            "annotations": dict(annotations or {}),
        }
        if session_id:
            package["session_id"] = session_id
        return package


def default_runner() -> ObservationRunner:
    """Text + consistency + behavioral observers (work on plain transcripts)."""
    return ObservationRunner(
        observers=[
            HedgingObserver(),
            PronounDistancingObserver(),
            NegationDensityObserver(),
            DetailVaguenessObserver(),
            CertaintySwingObserver(),
            MinimizationObserver(),
            PassiveVoiceProxyObserver(),
            OverjustificationObserver(),
            MemoryQualifierObserver(),
            ClaimConflictObserver(),
            TimelineInconsistencyObserver(),
            DetailDriftObserver(),
            LocationReferenceDivergenceObserver(),
            SelfReferenceShiftObserver(),
            ResponseLatencyObserver(),
            AnswerLengthVarianceObserver(),
            EvasionMarkerObserver(),
            SpeechRateShiftObserver(),
            FilledPauseMarkerObserver(),
            InterruptionOverlapObserver(),
        ]
    )


def full_runner() -> ObservationRunner:
    """All observers, including prosody/visual/physiological feature adapters.

    Feature-based modalities emit no observations (only notes internally) when the
    required metadata is absent.
    """
    r = default_runner()
    r.observers.extend([
        ProsodicVariabilityObserver(),
        PausePatternObserver(),
        VoiceStressFeatureShiftObserver(),
        GazePatternObserver(),
        BlinkRateObserver(),
        MotorActivityObserver(),
        HeartRateShiftObserver(),
        HrvShiftObserver(),
        ElectrodermalShiftObserver(),
    ])
    return r
