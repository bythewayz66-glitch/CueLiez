"""Visual/behavioral-feature observation methods.

Operates on caller-provided annotated visual features per turn/window (e.g.,
gaze, blink, gesture summaries). No raw video processing is performed.
Observations are cues for human review, not verdicts.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, source_span


def _feat(turn: Any, *keys: str) -> float | None:
    if not isinstance(turn, Mapping):
        return None
    for k in keys:
        v = turn.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    for container in ("visual", "video_features", "vision", "features", "meta", "metadata"):
        c = turn.get(container)
        if isinstance(c, Mapping):
            for k in keys:
                v = c.get(k)
                if isinstance(v, (int, float)):
                    return float(v)
    return None


class GazePatternObserver:
    method_id = "cueliez.observations.visual.gaze_pattern/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "gaze_aversion_ratio", "gaze_away_ratio", "averted_gaze_ratio")
            if v is not None and 0 <= v <= 1:
                vals.append((i, v))
        if len(vals) < 3:
            result.notes.append("insufficient_visual_gaze_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1e-9
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.0:
                score = clamp01(0.35 + min(abs(z), 6.0) * 0.08)
                direction = "higher" if v > med else "lower"
                result.observations.append(make_observation(
                    label="gaze_pattern_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="visual",
                    evidence={"gaze_aversion_ratio": v, "median": med, "robust_z": round(z, 3), "direction": direction, **source_span(turn, i)},
                    cue=f"Gaze aversion ratio was {direction} than baseline; consider cultural norms, comfort, and question context.",
                    turn_index=i,
                ))
        return result


class BlinkRateObserver:
    method_id = "cueliez.observations.visual.blink_rate/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "blink_rate_per_min", "blink_rate", "blinks_per_minute")
            if v is not None and 0 <= v <= 120:
                vals.append((i, v))
        if len(vals) < 3:
            result.notes.append("insufficient_blink_data")
            return result
        series = [v for _, v in vals]
        med = statistics.median(series)
        mad = statistics.median([abs(v - med) for v in series]) or 1.0
        for i, v in vals:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.2:
                score = clamp01(0.34 + min(abs(z), 6.0) * 0.07)
                direction = "higher" if v > med else "lower"
                result.observations.append(make_observation(
                    label="blink_rate_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="visual",
                    evidence={"blink_rate_per_min": v, "median": med, "robust_z": round(z, 3), "direction": direction, **source_span(turn, i)},
                    cue=f"Blink rate was {direction} than baseline; interpret only alongside context and other observations.",
                    turn_index=i,
                ))
        return result


class MotorActivityObserver:
    method_id = "cueliez.observations.visual.motor_activity/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            g = _feat(turn, "gesture_count", "hand_movement_events")
            h = _feat(turn, "head_movement_events", "head_motion_events")
            p = _feat(turn, "posture_shift_count", "posture_shifts")
            parts = [x for x in (g, h, p) if x is not None and x >= 0]
            if parts:
                vals.append((i, sum(parts)))
        if len(vals) < 3:
            result.notes.append("insufficient_motor_activity_data")
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
                    label="motor_activity_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="visual",
                    evidence={"activity_index": v, "median": med, "robust_z": round(z, 3), "direction": direction, **source_span(turn, i)},
                    cue=f"Observed motor activity was {direction} than baseline; consider environment and individual baseline.",
                    turn_index=i,
                ))
        return result
