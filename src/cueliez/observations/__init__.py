"""Observation methods for CueLiez.

These modules produce *observations and cues* (probabilistic indicators) for
officer review. They never produce deception verdicts, guilt findings, or
definitive truth claims.
"""

from .base import Observation, ObservationResult, make_observation
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
from .multimodal import CrossModalConvergenceObserver, add_convergence_observations
from .physiological import ElectrodermalShiftObserver, HeartRateShiftObserver, HrvShiftObserver
from .prosody import PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver
from .runner import ObservationRunner, default_runner, full_runner
from .visual import BlinkRateObserver, GazePatternObserver, MotorActivityObserver

__all__ = [
    "Observation",
    "ObservationResult",
    "make_observation",
    "AnswerLengthVarianceObserver",
    "EvasionMarkerObserver",
    "FilledPauseMarkerObserver",
    "InterruptionOverlapObserver",
    "ResponseLatencyObserver",
    "SpeechRateShiftObserver",
    "ClaimConflictObserver",
    "DetailDriftObserver",
    "LocationReferenceDivergenceObserver",
    "SelfReferenceShiftObserver",
    "TimelineInconsistencyObserver",
    "CertaintySwingObserver",
    "DetailVaguenessObserver",
    "HedgingObserver",
    "MemoryQualifierObserver",
    "MinimizationObserver",
    "NegationDensityObserver",
    "OverjustificationObserver",
    "PassiveVoiceProxyObserver",
    "PronounDistancingObserver",
    "CrossModalConvergenceObserver",
    "add_convergence_observations",
    "ElectrodermalShiftObserver",
    "HeartRateShiftObserver",
    "HrvShiftObserver",
    "PausePatternObserver",
    "ProsodicVariabilityObserver",
    "VoiceStressFeatureShiftObserver",
    "BlinkRateObserver",
    "GazePatternObserver",
    "MotorActivityObserver",
    "ObservationRunner",
    "default_runner",
    "full_runner",
]
