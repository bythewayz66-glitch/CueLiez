"""Gated derived-feature observers (owner decision, 2026-11-25).

These observers cover the capabilities the owner reversed from the
earlier "permanently excluded" list. They are GATED, consent-required,
and OFF by default — never on silently, never definitive findings:

- :class:`FacePresenceConsistencyObserver` — derived-feature consistency
  only (no identification, no match score).
- :class:`FaceRecognitionObserver` — REAL enrollment + embedding-distance
  matching via :mod:`cueliez.observations.face_recognition` (OpenFace
  embeddings, Haar detection, landmark alignment). Reports real
  distances and a distance-derived similarity score, or nothing at all
  when the optional dependency / enrollment / consent is absent.
- :class:`DemographicInferenceObserver` — HIGH-RISK, bias-prone,
  admissibility-sensitive. Behind its OWN SEPARATE gate (see
  :func:`cueliez.observations.modality_gates.check_demographic_inference_allowed`),
  never folded into the general modality gate. Reports only caller-supplied
  derived attributes, with a low score ceiling and a bias caveat.
- :class:`ExpressionFeatureObserver` — reports only caller-supplied
  derived expression features, with a caveat; never a definitive
  expression/emotion classification.
- :class:`PitchVoiceQualityObserver` — reports caller-supplied
  pitch/voice-quality feature shifts.
- :class:`WearableFeatureObserver` — reports caller-supplied wearable
  feature shifts.

What NONE of these observers do (stated per observer in its docstring):

- No real recognition is claimed where only derived features exist
  (presence/expression/demographic/pitch/wearable observers report
  supplied data only).
- No biometric template is created or matched by the derived-feature
  observers; templates exist only inside
  :mod:`cueliez.observations.face_recognition` enrollment, guarded by
  face-recognition consent + jurisdiction.
- No cloud call is made by any observer in this module.
- No observation here is a finding about a person: every label is a
  neutral cue for human review, with confidence capped as documented.

Gating contract: every observer in this module is constructed disabled
(``enabled=False``). It emits nothing until explicitly enabled — either
via the constructor, via ``observe_with_context(..., enabled=True)``, or
via the runner's ``enabled_gated_observers`` set — AND, when a gate
state is supplied, the relevant consent check passes (general modality
consent for face/pitch/wearable; the SEPARATE demographic gate for
demographic inference). Being listed in a runner (e.g. ``full_runner``)
does NOT enable an observer.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .base import (
    ObservationResult,
    clamp01,
    feature_dict,
    feature_value,
    is_subject_turn,
    make_observation,
    source_span,
    text_of,
)
from .modality_gates import check_demographic_inference_allowed, check_modality_allowed

# Score ceilings: gated observers never report high confidence, because
# their inputs are supplied derived features (or, for face matching, a
# similarity derived from an embedding distance on a small fixture).
_DEMOGRAPHIC_SCORE_CAP = 0.45
_EXPRESSION_SCORE_CAP = 0.50
_FACE_PRESENCE_SCORE_CAP = 0.60
_PITCH_SCORE_CAP = 0.60
_WEARABLE_SCORE_CAP = 0.60

_BIAS_CAVEAT = (
    "Supplied attributes only; high risk of bias and error; "
    "admissibility-sensitive; do not use as a finding about the person."
)


def _robust_z_outliers(values: List[tuple[int, float]], *, z_min: float = 2.0):
    """Yield (turn_index, value, median, z) for robust-z outliers."""
    if len(values) < 3:
        return
    series = [v for _, v in values]
    med = statistics.median(series)
    mad = statistics.median([abs(v - med) for v in series]) or 1e-9
    for i, v in values:
        z = (v - med) / (1.4826 * mad)
        if abs(z) >= z_min:
            yield i, v, med, z


class _GatedObserverBase:
    """Shared opt-in + consent plumbing for gated observers."""

    method_id = "cueliez.observations.gated.base/v1"
    gated_modality: Optional[str] = None  # canonical modality, or None
    requires_opt_in = True

    def __init__(self, *, enabled: bool = False, gate_state: Any = None) -> None:
        self.enabled = bool(enabled)
        self.gate_state = gate_state

    def _resolve(self, enabled: Optional[bool], gate_state: Any):
        en = self.enabled if enabled is None else bool(enabled)
        gs = self.gate_state if gate_state is None else gate_state
        return en, gs

    def _gate_check(self, gate_state: Any, *, separate_demographic: bool = False) -> Optional[str]:
        """Return a note when the gate blocks this observer, else None."""
        if gate_state is None:
            return None
        try:
            if separate_demographic:
                check_demographic_inference_allowed(gate_state)
            elif self.gated_modality:
                check_modality_allowed(gate_state, self.gated_modality)
        except Exception as exc:  # GateError (fail closed) or import issue
            return f"gated_modality_not_allowed: {exc}"
        return None


class FacePresenceConsistencyObserver(_GatedObserverBase):
    """Derived face-presence / feature-consistency observer (gated).

    Reports ONLY consistency/variation in caller-supplied derived face
    features (``face_presence``, ``face_feature_stability``,
    ``face_present_ratio``). It does NOT identify anyone, does NOT
    produce a match score, does NOT create or compare a biometric
    template, and makes NO cloud call. A real match is the job of
    :class:`FaceRecognitionObserver`, which needs enrollment + consent.
    """

    method_id = "cueliez.observations.gated.face_presence_consistency/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs)
        if blocked:
            result.notes.append(blocked)
            return result
        presence: List[tuple[int, float, Any]] = []
        stability: List[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            p = feature_value(turn, "face_presence", "face_present", "face_present_ratio")
            if p is not None and 0.0 <= p <= 1.0:
                presence.append((i, p, turn))
            s = feature_value(turn, "face_feature_stability", "face_stability")
            if s is not None and 0.0 <= s <= 1.0:
                stability.append((i, s, turn))
        if len(presence) < 3 and len(stability) < 3:
            result.notes.append("insufficient_face_feature_data")
            return result
        flips = sum(1 for a, b in zip(presence, presence[1:]) if (a[1] >= 0.5) != (b[1] >= 0.5))
        stab_range = (max(v for _, v, _ in stability) - min(v for _, v, _ in stability)) if len(stability) >= 3 else 0.0
        if flips == 0 and stab_range < 0.3:
            result.notes.append("no_face_feature_consistency_variation")
            return result
        anchor_i, _, anchor_turn = presence[-1] if presence else stability[-1]
        score = clamp01(min(_FACE_PRESENCE_SCORE_CAP, 0.35 + 0.10 * flips + 0.5 * stab_range))
        ev: Dict[str, Any] = {
            "face_presence_samples": len(presence),
            "presence_flips": flips,
            "feature_stability_range": round(stab_range, 4),
            "caveat": "Derived face-feature consistency only; not identification, "
                      "not a match score; no biometric template created or compared.",
        }
        if anchor_turn is not None:
            ev.update(source_span(anchor_turn, anchor_i))
        result.observations.append(make_observation(
            label="face_feature_consistency_variation_observed",
            score=score,
            method_id=self.method_id,
            category="visual",
            evidence=ev,
            cue="Supplied face-feature values varied across turns; review the corresponding video segment and tracking quality.",
            turn_index=anchor_i,
        ))
        return result


class FaceRecognitionObserver(_GatedObserverBase):
    """REAL face recognition observer (gated): enrollment + matching.

    Uses a :class:`cueliez.observations.face_recognition.FaceRecognizer`
    supplied at construction (OpenFace 128-d embeddings, landmark-aligned,
    Euclidean distance against enrolled mean embeddings). Reports the
    REAL measured distance and the distance-derived similarity score for
    a probe image that matches an enrolled subject within threshold, or
    emits nothing when there is no match, no enrollment, no image, no
    recognizer, or no consent. It never invents a subject id or a score:
    without the optional dependency installed, the recognizer cannot be
    built and this observer only records ``face_recognizer_unavailable``.

    Gate: explicit opt-in (``enabled``) + camera-modality consent and
    jurisdiction when a gate state is supplied. Enrollment itself must
    have happened under face-recognition consent; templates are sensitive
    biometric data (see ``face_recognition.FaceTemplateStore``).
    """

    method_id = "cueliez.observations.gated.face_recognition/v1"
    gated_modality = "camera"

    def __init__(
        self,
        recognizer: Any = None,
        *,
        enabled: bool = False,
        gate_state: Any = None,
    ) -> None:
        super().__init__(enabled=enabled, gate_state=gate_state)
        self.recognizer = recognizer

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs)
        if blocked:
            result.notes.append(blocked)
            return result
        if self.recognizer is None:
            result.notes.append("face_recognizer_not_configured")
            return result
        try:
            from .face_recognition import NoFaceDetected
        except Exception:  # pragma: no cover
            NoFaceDetected = ValueError  # type: ignore[assignment, misc]
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            image_ref = None
            if isinstance(turn, Mapping):
                image_ref = turn.get("face_image") or turn.get("face_image_path")
                if image_ref is None:
                    image_ref = feature_dict(turn).get("face_image") or feature_dict(turn).get("face_image_path")
            if image_ref is None:
                continue
            try:
                match = self.recognizer.match(image_ref)
            except NoFaceDetected:
                result.notes.append(f"no_face_detected_turn_{i}")
                continue
            except Exception as exc:
                result.notes.append(f"face_match_error_turn_{i}: {exc}")
                continue
            if not match.matched:
                result.notes.append(f"no_face_match_turn_{i}")
                continue
            ev: Dict[str, Any] = {
                "subject_id": match.subject_id,
                "embedding_distance": match.distance,
                "similarity_score": round(match.score, 4),
                "match_threshold": match.threshold,
                "model": match.model,
                "aligned": match.aligned,
                "enrolled_subjects": list(match.enrolled_subjects),
                "caveat": "Embedding-distance match against enrolled templates; a similarity "
                          "cue for human review, not a definitive identification. Score is a "
                          "linear similarity from embedding distance, not a probability.",
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="face_match_observed",
                score=match.score,
                method_id=self.method_id,
                category="visual",
                evidence=ev,
                cue="Probe image matched an enrolled subject by embedding distance; confirm identity through the normal human process.",
                turn_index=i,
            ))
        return result


class DemographicInferenceObserver(_GatedObserverBase):
    """Demographic-inference observer — HIGH-RISK, separate gate only.

    Reports ONLY caller-supplied derived attributes (``features`` /
    ``demographic_attributes`` as supplied by the caller, e.g. from an
    upstream component). It performs NO inference itself: there is no
    classifier, no model, and no attribute is derived here. Scores are
    capped at 0.45 and every observation carries a bias/admissibility
    caveat. It does NOT produce a finding about a person, and its output
    must never be used as one.

    Gate (separate, owner decision 2026-11-25): explicit opt-in
    (``enabled``) AND the SEPARATE demographic-inference consent record
    (``cueliez.gates.require_demographic_inference_consent``) when a gate
    state is supplied. General modality consent (camera/audio/wearable)
    NEVER enables this observer.
    """

    method_id = "cueliez.observations.gated.demographic_inference/v1"
    gated_modality = None  # Deliberate: NOT a general-modality observer.

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs, separate_demographic=True)
        if blocked:
            result.notes.append(blocked)
            return result
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            feats = feature_dict(turn)
            attrs = feats.get("demographic_attributes")
            if not isinstance(attrs, Mapping) or not attrs:
                continue
            supplied = {str(k): v for k, v in attrs.items()}
            score = clamp01(min(_DEMOGRAPHIC_SCORE_CAP, 0.30 + 0.03 * len(supplied)))
            ev: Dict[str, Any] = {
                "supplied_demographic_attributes": supplied,
                "attribute_count": len(supplied),
                "bias_caveat": _BIAS_CAVEAT,
                "gate": "demographic_inference (separate opt-in record)",
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="supplied_demographic_attributes_noted",
                score=score,
                method_id=self.method_id,
                category="context",
                evidence=ev,
                cue="Supplied demographic attributes were noted for this turn; treat as supplied data only and review for bias before any use.",
                turn_index=i,
            ))
        if not result.observations:
            result.notes.append("no_supplied_demographic_attributes")
        return result


class ExpressionFeatureObserver(_GatedObserverBase):
    """Derived expression-feature observer (gated).

    Reports ONLY caller-supplied derived expression features
    (``features`` / ``expression_features``, e.g. named measurements such
    as brow/eye/mouth movement summaries). It does NOT classify any
    expression or emotion, does NOT infer an inner state, and makes NO
    cloud call. Scores are capped at 0.50 and every observation carries
    a caveat stating no definitive expression classification is made.
    """

    method_id = "cueliez.observations.gated.expression_features/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs)
        if blocked:
            result.notes.append(blocked)
            return result
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            feats = feature_dict(turn)
            expr = feats.get("expression_features")
            if not isinstance(expr, Mapping) or not expr:
                continue
            supplied = {str(k): v for k, v in expr.items()}
            numeric = {k: float(v) for k, v in supplied.items() if isinstance(v, (int, float))}
            score = clamp01(min(_EXPRESSION_SCORE_CAP, 0.30 + 0.04 * len(supplied)))
            ev: Dict[str, Any] = {
                "supplied_expression_features": supplied,
                "feature_count": len(supplied),
                "caveat": "Supplied derived expression features only; not an expression "
                          "classification and not a finding about any inner state.",
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="supplied_expression_features_noted",
                score=score,
                method_id=self.method_id,
                category="visual",
                evidence=ev,
                cue="Supplied derived expression features were noted for this turn; interpret only alongside context and other observations.",
                turn_index=i,
            ))
        if not result.observations:
            result.notes.append("no_supplied_expression_features")
        return result


class PitchVoiceQualityObserver(_GatedObserverBase):
    """Pitch / voice-quality derived-feature observer (gated).

    Reports robust-z shifts in caller-supplied pitch/voice-quality
    features (``f0_mean_hz``, ``f0_std_hz``, ``pitch_range_hz``,
    ``jitter``, ``shimmer``) against the session baseline. It processes
    NO raw audio, performs NO voice identification, and makes NO cloud
    call. Scores are capped at 0.60.
    """

    method_id = "cueliez.observations.gated.pitch_voice_quality/v1"
    gated_modality = "audio_features"
    _KEYS = ("f0_mean_hz", "f0_std_hz", "pitch_range_hz", "jitter", "shimmer")

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs)
        if blocked:
            result.notes.append(blocked)
            return result
        per_key: Dict[str, List[tuple[int, float]]] = {k: [] for k in self._KEYS}
        turn_by_index: Dict[int, Any] = {}
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            turn_by_index[i] = turn
            for k in self._KEYS:
                v = feature_value(turn, k)
                if v is not None:
                    per_key[k].append((i, v))
        found_any = False
        for k, vals in per_key.items():
            if len(vals) < 3:
                continue
            found_any = True
            for i, v, med, z in _robust_z_outliers(vals, z_min=2.5):
                score = clamp01(min(_PITCH_SCORE_CAP, 0.35 + min(abs(z), 6.0) * 0.07))
                direction = "higher" if v > med else "lower"
                ev: Dict[str, Any] = {
                    "feature": k,
                    "value": v,
                    "median": med,
                    "robust_z": round(z, 3),
                    "direction": direction,
                    "caveat": "Supplied pitch/voice-quality feature shift only; not a "
                              "voice identification and not a finding about any state.",
                }
                ev.update(source_span(turn_by_index[i], i))
                result.observations.append(make_observation(
                    label="pitch_voice_quality_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="prosody",
                    evidence=ev,
                    cue=f"Supplied pitch/voice-quality feature ({k}) was {direction} than baseline; treat as a contextual signal, not a determination.",
                    turn_index=i,
                ))
        if not found_any:
            result.notes.append("insufficient_pitch_voice_quality_data")
        return result


class WearableFeatureObserver(_GatedObserverBase):
    """Wearable / physiological derived-feature observer (gated).

    Reports robust-z shifts in caller-supplied wearable features
    (``features`` / ``wearable`` sub-dict: numeric keys such as
    ``skin_temperature_c``, ``spo2``, ``movement_count``). It accesses
    NO sensor, performs NO medical inference, and makes NO cloud call.
    Scores are capped at 0.60. Wearable consent + jurisdiction apply
    when a gate state is supplied.
    """

    method_id = "cueliez.observations.gated.wearable_features/v1"
    gated_modality = "wearable"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        return self.observe_with_context(transcript, enabled=self.enabled, gate_state=self.gate_state)

    def observe_with_context(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        enabled: Optional[bool] = None,
        gate_state: Any = None,
    ) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        en, gs = self._resolve(enabled, gate_state)
        if not en:
            result.notes.append("gated_observer_disabled")
            return result
        blocked = self._gate_check(gs)
        if blocked:
            result.notes.append(blocked)
            return result
        per_key: Dict[str, List[tuple[int, float]]] = {}
        turn_by_index: Dict[int, Any] = {}
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            turn_by_index[i] = turn
            wearable = feature_dict(turn).get("wearable")
            if not isinstance(wearable, Mapping):
                continue
            for k, v in wearable.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    per_key.setdefault(str(k), []).append((i, float(v)))
        found_any = False
        for k, vals in sorted(per_key.items()):
            if len(vals) < 3:
                continue
            found_any = True
            for i, v, med, z in _robust_z_outliers(vals, z_min=2.0):
                score = clamp01(min(_WEARABLE_SCORE_CAP, 0.35 + min(abs(z), 6.0) * 0.07))
                direction = "higher" if v > med else "lower"
                ev: Dict[str, Any] = {
                    "feature": k,
                    "value": v,
                    "median": med,
                    "robust_z": round(z, 3),
                    "direction": direction,
                    "caveat": "Supplied wearable feature shift only; not a medical "
                              "finding and not a determination of intent.",
                }
                ev.update(source_span(turn_by_index[i], i))
                result.observations.append(make_observation(
                    label="wearable_feature_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="physiological",
                    evidence=ev,
                    cue=f"Supplied wearable feature ({k}) was {direction} than baseline (provided measurement). Not a medical finding.",
                    turn_index=i,
                ))
        if not found_any:
            result.notes.append("insufficient_wearable_feature_data")
        return result
