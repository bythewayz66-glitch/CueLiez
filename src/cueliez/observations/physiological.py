"""Physiological-feature observation methods.

Operates ONLY on caller-provided, consent-governed measurement summaries
(e.g., heart rate, HRV). No sensors are accessed by this module.
Observations are activation/arousal-pattern cues for human review, not medical
diagnoses and not deception determinations.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation


def _feat(turn: Any, *keys: str) -> float | None:
    if not isinstance(turn, Mapping):
        return None
    for k in keys:
        v = turn.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    for container in ("physio", "physiological", "biometric_features", "features", "meta", "metadata"):
        c = turn.get(container)
        if isinstance(c, Mapping):
            for k in keys:
                v = c.get(k)
                if isinstance(v, (int, float)):
                    return float(v)
    return None


class HeartRateShiftObserver:
    method_id = "cueliez.observations.physiological.heart_rate_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "heart_rate_bpm", "hr_bpm", "pulse_bpm")
            if v is not None and 30 <= v <= 220:
                vals.append((i, v))
        if len(vals) < 3:
            result.notes.append("insufficient_heart_rate_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1.0
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.0:
                score = clamp01(0.35 + min(abs(z), 6.0) * 0.07)
                direction = "higher" if v > med else "lower"
                result.observations.append(make_observation(
                    label="heart_rate_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="physiological",
                    evidence={"heart_rate_bpm": v, "median_bpm": med, "robust_z": round(z, 3), "direction": direction},
                    cue=f"Heart rate was {direction} than baseline (provided measurement). Activation indicators are not determinations of intent or truthfulness.",
                    turn_index=i,
                ))
        return result


class HrvShiftObserver:
    method_id = "cueliez.observations.physiological.hrv_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "hrv_ms", "hrv_rmssd_ms", "rmssd_ms")
            if v is not None and 0 <= v <= 500:
                vals.append((i, v))
        if len(vals) < 3:
            result.notes.append("insufficient_hrv_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1.0
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.0:
                score = clamp01(0.33 + min(abs(z), 6.0) * 0.07)
                direction = "higher" if v > med else "lower"
                result.observations.append(make_observation(
                    label="hrv_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="physiological",
                    evidence={"hrv_ms": v, "median_ms": med, "robust_z": round(z, 3), "direction": direction},
                    cue=f"HRV measure was {direction} than baseline (provided measurement). Not a medical finding or determination of intent.",
                    turn_index=i,
                ))
        return result


class ElectrodermalShiftObserver:
    method_id = "cueliez.observations.physiological.electrodermal_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "skin_conductance", "eda", "gsr", "scr_count")
            if v is not None and v >= 0:
                vals.append((i, v))
        if len(vals) < 3:
            result.notes.append("insufficient_electrodermal_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1e-9
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if z >= 2.2:
                score = clamp01(0.34 + min(z, 6.0) * 0.07)
                result.observations.append(make_observation(
                    label="electrodermal_activity_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="physiological",
                    evidence={"value": v, "median": med, "robust_z": round(z, 3)},
                    cue="Electrodermal activity shifted from baseline (provided measurement). Activation indicators are not determinations of intent or truthfulness.",
                    turn_index=i,
                ))
        return result
