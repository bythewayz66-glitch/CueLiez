"""Observation methods for CueLiez.

These modules produce *observations and cues* (probabilistic indicators) for
officer review. They never produce deception verdicts, guilt findings, or
definitive truth claims.
"""

from .base import Observation, ObservationResult, feature_dict, feature_value, make_observation, source_span, truncate_source
from .behavioral import (
    AnswerLengthVarianceObserver,
    EvasionMarkerObserver,
    FilledPauseClusterObserver,
    FilledPauseMarkerObserver,
    InterruptionOverlapObserver,
    ResponseLatencyObserver,
    ResponseLatencyShiftObserver,
    SpeechRateShiftObserver,
    SpeechRateTrendObserver,
)
from .consistency import (
    ClaimConflictObserver,
    CrossTurnClaimRestatementObserver,
    DetailDriftObserver,
    LocationReferenceDivergenceObserver,
    PronounShiftObserver,
    SelfReferenceShiftObserver,
    TimelineInconsistencyObserver,
)
from .face_recognition import (
    FaceMatch,
    FaceRecognitionError,
    FaceRecognitionUnavailable,
    FaceRecognizer,
    FaceTemplateStore,
    NoFaceDetected,
    face_available,
)
from .gated import (
    DemographicInferenceObserver,
    ExpressionFeatureObserver,
    FacePresenceConsistencyObserver,
    FaceRecognitionObserver,
    PitchVoiceQualityObserver,
    WearableFeatureObserver,
)
from .linguistic import (
    CertaintySwingObserver,
    DetailDensityShiftObserver,
    DetailVaguenessObserver,
    HedgingClusterObserver,
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
from .prosody import PauseDensityShiftObserver, PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver
from .runner import ObservationRunner, default_runner, full_runner, load_features_file, merge_features_into_turns
from .visual import (
    BlinkRateObserver,
    BlinkRateTrendObserver,
    GazePatternObserver,
    MotorActivityObserver,
    OffCameraGazeFrequencyObserver,
    RestlessnessShiftObserver,
)
from .narrative import (
    TemporalStructureObserver,
    SensoryDetailObserver,
    AgencyFramingObserver,
    SpecificityShiftObserver,
)

__all__ = [
    "Observation",
    "ObservationResult",
    "make_observation",
    "feature_value",
    "feature_dict",
    "AnswerLengthVarianceObserver",
    "EvasionMarkerObserver",
    "FilledPauseClusterObserver",
    "FilledPauseMarkerObserver",
    "InterruptionOverlapObserver",
    "ResponseLatencyObserver",
    "ResponseLatencyShiftObserver",
    "SpeechRateShiftObserver",
    "SpeechRateTrendObserver",
    "ClaimConflictObserver",
    "CrossTurnClaimRestatementObserver",
    "DetailDriftObserver",
    "LocationReferenceDivergenceObserver",
    "PronounShiftObserver",
    "SelfReferenceShiftObserver",
    "TimelineInconsistencyObserver",
    "FaceMatch",
    "FaceRecognitionError",
    "FaceRecognitionUnavailable",
    "FaceRecognizer",
    "FaceTemplateStore",
    "NoFaceDetected",
    "face_available",
    "DemographicInferenceObserver",
    "ExpressionFeatureObserver",
    "FacePresenceConsistencyObserver",
    "FaceRecognitionObserver",
    "PitchVoiceQualityObserver",
    "WearableFeatureObserver",
    "CertaintySwingObserver",
    "DetailDensityShiftObserver",
    "DetailVaguenessObserver",
    "HedgingClusterObserver",
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
    "PauseDensityShiftObserver",
    "PausePatternObserver",
    "ProsodicVariabilityObserver",
    "VoiceStressFeatureShiftObserver",
    "BlinkRateObserver",
    "BlinkRateTrendObserver",
    "GazePatternObserver",
    "MotorActivityObserver",
    "OffCameraGazeFrequencyObserver",
    "RestlessnessShiftObserver",
    "TemporalStructureObserver",
    "SensoryDetailObserver",
    "AgencyFramingObserver",
    "SpecificityShiftObserver",
    "ObservationRunner",
    "default_runner",
    "full_runner",
    "load_features_file",
    "merge_features_into_turns",
]
