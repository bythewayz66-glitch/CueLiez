"""Prosody/voice-feature observation methods.

Operates on caller-provided acoustic feature metadata per turn (e.g., pitch,
speech timing summaries). No raw audio processing is performed. Observations
are cues for human review, not verdicts.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, text_of


def _feat(turn: Any, *keys: str) -> float | None:
    if not isinstance(turn, Mapping):
        return None
    for k in keys:
        v = turn.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    for container in ("prosody", "acoustic", "audio_features", "features", "meta", "metadata"):
        c = turn.get(container)
        if isinstance(c, Mapping):
            for k in keys:
                v = c.get(k)
                if isinstance(v, (int, float)):
                    return float(v)
    return None


class ProsodicVariabilityObserver:
    method_id = "cueliez.observations.prosody.variability_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float, str]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            # pitch variance / f0 stddev / intensity variance proxy
            v = _feat(turn, "pitch_variance", "f0_stddev_hz", "pitch_std_hz", "intensity_variance")
            if v is not None and v >= 0:
                vals.append((i, v, "pitch_or_intensity_variance"))
        if len(vals) < 3:
            result.notes.append("insufficient_prosody_data")
            return result
        series = [v for _, v, _ in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1e-9
        for i, v, kind in vals:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.0:
                score = clamp01(0.38 + min(abs(z), 6.0) * 0.08)
                direction = "higher" if v > med else "lower"
                result.observations.append(make_observation(
                    label="prosodic_variability_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="prosody",
                    evidence={"value": v, "median": med, "robust_z": round(z, 3), "direction": direction, "feature": kind},
                    cue=f"Prosodic variability was {direction} than session baseline; review the corresponding question/context.",
                    turn_index=i,
                ))
        return result


class PausePatternObserver:
    method_id = "cueliez.observations.prosody.pause_pattern/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            p = _feat(turn, "pause_total_ms", "pause_duration_ms", "silence_ms")
            if p is None:
                pc = _feat(turn, "pause_count")
                if pc is not None:
                    p = pc * 300.0  # coarse proxy only when explicit duration absent
            if p is not None and p >= 0:
                vals.append((i, p))
        if len(vals) < 3:
            result.notes.append("insufficient_pause_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1.0
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if z >= 2.2 and v >= 500:
                score = clamp01(0.4 + min(z, 6.0) * 0.07)
                result.observations.append(make_observation(
                    label="pause_duration_elevated_observed",
                    score=score,
                    method_id=self.method_id,
                    category="prosody",
                    evidence={"pause_proxy_ms": v, "median_ms": med, "robust_z": round(z, 3)},
                    cue="Pause/silence duration was elevated relative to baseline; consider question difficulty and allow processing time.",
                    turn_index=i,
                ))
        return result


class VoiceStressFeatureShiftObserver:
    method_id = "cueliez.observations.prosody.voice_feature_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        # Generic named features; caller must not interpret as deception.
        keys = ("jitter", "shimmer", "hnr", "spectral_tilt", "formant_dispersion")
        per_key: dict[str, list[tuple[int, float]]] = {k: [] for k in keys}
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            for k in keys:
                v = _feat(turn, k)
                if v is not None:
                    per_key[k].append((i, v))
        found_any = False
        for k, vals in per_key.items():
            if len(vals) < 3:
                continue
            found_any = True
            series = [v for _, v in vals]
            med = statistics.median(series)
            mad = statistics.median([abs(v - med) for v in series]) or 1e-9
            for i, v in vals:
                z = abs(v - med) / (1.4826 * mad)
                if z >= 2.5:
                    score = clamp01(0.35 + min(z, 6.0) * 0.07)
                    result.observations.append(make_observation(
                        label="acoustic_feature_shift_observed",
                        score=score,
                        method_id=self.method_id,
                        category="prosody",
                        evidence={"feature": k, "value": v, "median": med, "robust_z": round((v - med) / (1.4826 * mad), 3)},
                        cue="An acoustic feature shifted from baseline; treat as a contextual signal, not a determination.",
                        turn_index=i,
                    ))
        if not found_any:
            result.notes.append("insufficient_acoustic_feature_data")
        return result
