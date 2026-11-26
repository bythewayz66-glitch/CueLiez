"""Run observation methods and build gate-compatible packages.

Feature-metadata path (Track B): observers that need derived features
(prosody / visual / physiological, and the gated observers) read
caller-supplied feature metadata. Metadata reaches the runner in any of
these ways (no CLI change; the CLI keeps passing transcripts through):

- Per-turn ``"features"`` dicts, e.g.
  ``{"role": "subject", "text": "...", "features": {"audio_features": {"pitch_variance": 12.0}}}``
  (nested ``audio_features`` / ``camera`` / ``wearable`` sub-dicts are
  understood, as are flat top-level feature keys). Ingest preserves
  these keys on canonical turns.
- ``run(..., features=...)`` / ``build_package(..., features=...)``:
  a list aligned with the turns, or a dict mapping turn index -> feature
  dict, merged into each turn's ``"features"`` dict.
- ``run(..., features_path="features.json")``: a JSON file holding any
  of the above shapes (list, ``{index: {...}}``, or a wrapper object
  with a ``"features"`` key).
- A wrapper transcript ``{"turns": [...], "features": ...}``: the
  wrapper-level features are merged the same way.

Feature observers are INCLUDED in ``default_runner()`` / ``full_runner()``
and in every pack, but they only FIRE when feature metadata is present.
When a ``gate_state`` is supplied to the runner, feature observers are
additionally filtered by modality consent (fail closed via
``modality_observers_allowed``); without a gate state, the legacy
behaviour applies — callers that supply feature metadata are
responsible for having obtained consent before capture, and the
consent-enforcing entry points (``audio_path`` / ``audio_stream``)
check it before features ever reach the runner.

Gated reversal observers (``observations.gated``) are included in
``full_runner()`` and in pack lists but are DISABLED by default: they
fire only when explicitly enabled (runner ``enabled_gated_observers``
names, a wrapper ``"gated_opt_in"`` list, or the observer's own
``enabled=True``) AND, when a gate state is supplied, the relevant
consent check passes (general modality consent, or the SEPARATE
demographic-inference gate for demographic inference).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping as AbcMapping, Sequence as AbcSequence
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from .base import ObservationResult, Observer
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
from .modality_gates import modality_observers_allowed
from .multimodal import CrossModalConvergenceObserver, add_convergence_observations
# --- Track C (assisted) hook: opt-in only, off by default. ---
# The runner never adds an assisted observer to self.observers (so
# default_runner()/full_runner() stay assisted-free); when enable_assisted
# is set, run() merges assisted observations afterwards via
# merge_default_assisted_observations, which uses registered adapters if
# any, else the deterministic multi-signal baseline. No network/ML calls.
from .assisted import merge_default_assisted_observations
from .narrative import (
    AgencyFramingObserver,
    SensoryDetailObserver,
    SpecificityShiftObserver,
    TemporalStructureObserver,
)
from .physiological import ElectrodermalShiftObserver, HeartRateShiftObserver, HrvShiftObserver
from .prosody import (
    PauseDensityShiftObserver,
    PausePatternObserver,
    ProsodicVariabilityObserver,
    VoiceStressFeatureShiftObserver,
)
from .visual import (
    BlinkRateObserver,
    BlinkRateTrendObserver,
    GazePatternObserver,
    MotorActivityObserver,
    OffCameraGazeFrequencyObserver,
    RestlessnessShiftObserver,
)

# Short names for the gated observers, for enabled_gated_observers sets
# and wrapper "gated_opt_in" lists.
GATED_SHORT_NAMES = {
    "cueliez.observations.gated.face_presence_consistency/v1": "face_presence_consistency",
    "cueliez.observations.gated.face_recognition/v1": "face_recognition",
    "cueliez.observations.gated.demographic_inference/v1": "demographic_inference",
    "cueliez.observations.gated.expression_features/v1": "expression_features",
    "cueliez.observations.gated.pitch_voice_quality/v1": "pitch_voice_quality",
    "cueliez.observations.gated.wearable_features/v1": "wearable_features",
}


def _gated_short_name(observer: Any) -> Optional[str]:
    return GATED_SHORT_NAMES.get(getattr(observer, "method_id", ""))


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


def _split_wrapper(transcript: Any) -> tuple[Sequence[Any], Any, List[str]]:
    """Return (turns, wrapper_features, wrapper_gated_opt_in)."""
    turns = _normalize_transcript(transcript)
    features: Any = None
    opt_in: List[str] = []
    if isinstance(transcript, AbcMapping):
        features = transcript.get("features")
        raw_opt = transcript.get("gated_opt_in") or transcript.get("enabled_gated_observers") or []
        if isinstance(raw_opt, (list, tuple)):
            opt_in = [str(x) for x in raw_opt]
    return turns, features, opt_in


def load_features_file(path: Union[str, Path]) -> Any:
    """Load a --features JSON file (list, {index: {...}}, or wrapper with 'features').

    Returns the decoded JSON value; callers pass it as ``features=``.
    Raises the underlying OSError / JSON error on unreadable input.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _features_for_turn(features: Any, index: int) -> Optional[Mapping[str, Any]]:
    if features is None:
        return None
    if isinstance(features, AbcMapping):
        # Wrapper shape {"features": ...} -> unwrap once.
        if "features" in features and not any(
            isinstance(k, (int, str)) and str(k).isdigit() for k in features
        ):
            return _features_for_turn(features.get("features"), index)
        v = features.get(index, features.get(str(index)))
        return v if isinstance(v, Mapping) else None
    if isinstance(features, AbcSequence) and not isinstance(features, (str, bytes)):
        if 0 <= index < len(features):
            v = features[index]
            return v if isinstance(v, Mapping) else None
    return None


def merge_features_into_turns(
    turns: Sequence[Any], features: Any
) -> List[Dict[str, Any]]:
    """Return copies of ``turns`` with ``features`` merged into each turn's 'features' dict.

    ``features`` may be a list aligned with the turns, a dict mapping
    turn index -> feature dict, or a wrapper ``{"features": ...}``.
    Existing per-turn features are preserved; supplied values win on
    key collision. Non-mapping turns are passed through unchanged.
    """
    out: List[Dict[str, Any]] = []
    for i, turn in enumerate(turns):
        if not isinstance(turn, AbcMapping):
            out.append(turn)  # type: ignore[arg-type]
            continue
        merged = dict(turn)
        extra = _features_for_turn(features, i)
        if extra:
            base = dict(merged.get("features") or {}) if isinstance(merged.get("features"), Mapping) else {}
            for k, v in extra.items():
                if isinstance(v, Mapping) and isinstance(base.get(k), Mapping):
                    nested = dict(base[k])
                    nested.update(v)
                    base[k] = nested
                else:
                    base[k] = v
            merged["features"] = base
        out.append(merged)
    return out


class ObservationRunner:
    def __init__(
        self,
        observers: Optional[Sequence[Observer]] = None,
        *,
        enable_assisted: bool = False,
        gate_state: Any = None,
        enabled_gated_observers: Optional[Sequence[str]] = None,
    ):
        self.observers: List[Observer] = list(observers) if observers is not None else []
        # Track C (assisted) hook: explicit opt-in only, OFF by default.
        self.enable_assisted: bool = bool(enable_assisted)
        self.gate_state: Any = gate_state
        self.enabled_gated_observers: frozenset = frozenset(enabled_gated_observers or [])

    def run(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enable_assisted: bool | None = None,
        gate_state: Any = None,
        enabled_gated_observers: Optional[Sequence[str]] = None,
        features: Any = None,
        features_path: Union[str, Path, None] = None,
    ) -> List[Dict[str, Any]]:
        turns, wrapper_features, wrapper_opt_in = _split_wrapper(transcript)
        if features_path is not None:
            features = load_features_file(features_path)
        if features is not None or wrapper_features is not None:
            turns = merge_features_into_turns(turns, features if features is not None else wrapper_features)
        effective_gate = self.gate_state if gate_state is None else gate_state
        enabled_names = set(self.enabled_gated_observers)
        if enabled_gated_observers:
            enabled_names.update(str(x) for x in enabled_gated_observers)
        enabled_names.update(wrapper_opt_in)

        observations: List[Dict[str, Any]] = []
        convergence_observers = []
        for obs in self.observers:
            # Convergence needs already-produced observations; run it after.
            if hasattr(obs, "observe_observations"):
                convergence_observers.append(obs)
                continue
            # Gated observers: explicit opt-in + consent, via their own hook.
            if hasattr(obs, "observe_with_context"):
                short = _gated_short_name(obs)
                en = bool(getattr(obs, "enabled", False)) or (short in enabled_names if short else False)
                res: ObservationResult = obs.observe_with_context(
                    turns, enabled=en, gate_state=effective_gate
                )
                observations.extend(res.to_dicts())
                continue
            # Feature observers: included in the list, but when a gate
            # state is supplied they only run when modality consent allows.
            modality = getattr(obs, "gated_modality", None)
            if modality and effective_gate is not None:
                if not modality_observers_allowed(effective_gate, modality):
                    continue
            res = obs.observe(turns)
            observations.extend(res.to_dicts())
        for obs in convergence_observers:
            res = obs.observe_observations(observations)
            observations.extend(res.to_dicts())
        # --- Track C (assisted) hook: merge only when explicitly enabled. ---
        assisted_on = self.enable_assisted if enable_assisted is None else bool(enable_assisted)
        if assisted_on:
            observations = merge_default_assisted_observations(observations, turns, enabled=True)
        return observations

    def build_package(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        session_id: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        include_convergence: bool = True,
        min_convergence_categories: int = 2,
        enable_assisted: bool | None = None,
        gate_state: Any = None,
        enabled_gated_observers: Optional[Sequence[str]] = None,
        features: Any = None,
        features_path: Union[str, Path, None] = None,
    ) -> Dict[str, Any]:
        observations = self.run(
            transcript,
            enable_assisted=enable_assisted,
            gate_state=gate_state,
            enabled_gated_observers=enabled_gated_observers,
            features=features,
            features_path=features_path,
        )
        if include_convergence:
            observations = add_convergence_observations(observations, min_categories=min_convergence_categories)
        package: Dict[str, Any] = {
            "observations": observations,
            "annotations": dict(annotations or {}),
        }
        if session_id:
            package["session_id"] = session_id
        return package


def _default_observers() -> List[Any]:
    """All text + narrative observers (default-on), in family order."""
    return [
        # Linguistic (text)
        HedgingObserver(),
        HedgingClusterObserver(),
        PronounDistancingObserver(),
        NegationDensityObserver(),
        DetailVaguenessObserver(),
        DetailDensityShiftObserver(),
        CertaintySwingObserver(),
        MinimizationObserver(),
        PassiveVoiceProxyObserver(),
        OverjustificationObserver(),
        MemoryQualifierObserver(),
        # Consistency (text, cross-turn)
        ClaimConflictObserver(),
        CrossTurnClaimRestatementObserver(),
        TimelineInconsistencyObserver(),
        DetailDriftObserver(),
        LocationReferenceDivergenceObserver(),
        SelfReferenceShiftObserver(),
        PronounShiftObserver(),
        # Behavioral (text / turn metadata)
        ResponseLatencyObserver(),
        ResponseLatencyShiftObserver(),
        AnswerLengthVarianceObserver(),
        EvasionMarkerObserver(),
        SpeechRateShiftObserver(),
        SpeechRateTrendObserver(),
        FilledPauseMarkerObserver(),
        FilledPauseClusterObserver(),
        InterruptionOverlapObserver(),
        # Narrative (text, session-level)
        TemporalStructureObserver(),
        SensoryDetailObserver(),
        AgencyFramingObserver(),
        SpecificityShiftObserver(),
        # Convergence (post-run; needs prior observations)
        CrossModalConvergenceObserver(),
    ]


def _feature_observers() -> List[Any]:
    """Prosody / visual / physiological feature observers.

    Included in every runner by default, but they emit nothing unless
    caller-supplied feature metadata is present (and, when a gate state
    is supplied, modality consent allows).
    """
    return [
        ProsodicVariabilityObserver(),
        PausePatternObserver(),
        PauseDensityShiftObserver(),
        VoiceStressFeatureShiftObserver(),
        GazePatternObserver(),
        OffCameraGazeFrequencyObserver(),
        BlinkRateObserver(),
        BlinkRateTrendObserver(),
        MotorActivityObserver(),
        RestlessnessShiftObserver(),
        HeartRateShiftObserver(),
        HrvShiftObserver(),
        ElectrodermalShiftObserver(),
    ]


def _gated_observers(*, face_recognizer: Any = None) -> List[Any]:
    """Gated reversal observers. Included in the list, DISABLED by default.

    ``face_recognizer`` (a ``face_recognition.FaceRecognizer``) must be
    supplied by the caller for real face matching; without one, the face
    observer records ``face_recognizer_not_configured`` and emits nothing.
    """
    return [
        FacePresenceConsistencyObserver(),
        FaceRecognitionObserver(recognizer=face_recognizer),
        DemographicInferenceObserver(),
        ExpressionFeatureObserver(),
        PitchVoiceQualityObserver(),
        WearableFeatureObserver(),
    ]


def default_runner(
    enable_assisted: bool = False,
    *,
    gate_state: Any = None,
    enabled_gated_observers: Optional[Sequence[str]] = None,
) -> ObservationRunner:
    """All text + narrative observers AND the feature observers (default-on).

    Feature observers are in the list but inert without feature metadata
    (and gated by modality consent when a gate state is supplied).
    Gated reversal observers are NOT in the default runner; use
    ``full_runner()`` for the full list (still disabled until opted in).
    Assisted observers are OFF by default; pass enable_assisted=True for
    the explicit opt-in (deterministic multi-signal baseline, no ML calls).
    """
    return ObservationRunner(
        enable_assisted=enable_assisted,
        gate_state=gate_state,
        enabled_gated_observers=enabled_gated_observers,
        observers=_default_observers() + _feature_observers(),
    )


def full_runner(
    enable_assisted: bool = False,
    *,
    gate_state: Any = None,
    enabled_gated_observers: Optional[Sequence[str]] = None,
    face_recognizer: Any = None,
) -> ObservationRunner:
    """All observers: default + the gated reversal observers.

    Gated observers are in the list but DISABLED by default; enable by
    name, e.g. ``enabled_gated_observers={"face_recognition",
    "demographic_inference"}`` — and pass a ``gate_state`` carrying the
    relevant consent (camera consent for face/pitch/wearable; the
    SEPARATE demographic-inference record for demographic inference).
    ``face_recognizer`` supplies the real enrollment/matching engine for
    face recognition; without it that observer emits nothing.
    """
    r = default_runner(
        enable_assisted=enable_assisted,
        gate_state=gate_state,
        enabled_gated_observers=enabled_gated_observers,
    )
    r.observers.extend(_gated_observers(face_recognizer=face_recognizer))
    return r
