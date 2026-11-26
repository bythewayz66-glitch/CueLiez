"""Visual/behavioral-feature observation methods.

Operates on caller-provided annotated visual features per turn/window (e.g.,
gaze, blink, gesture summaries). No raw video processing is performed.
Observations are cues for human review, not verdicts.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, feature_value, is_subject_turn, make_observation, source_span


def _feat(turn: Any, *keys: str) -> float | None:
    """Read a numeric derived visual feature (flat, ``features`` dict, or nested ``features.camera``)."""
    return feature_value(turn, *keys)


class GazePatternObserver:
    method_id = "cueliez.observations.visual.gaze_pattern/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            # Canonical live key first; legacy input keys stay accepted
            # so older callers keep working. Display wording is always
            # "off-camera gaze" (never the legacy term).
            v = _feat(turn, "off_camera_gaze_share", "gaze_aversion_ratio", "gaze_away_ratio", "averted_gaze_ratio")
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
                    evidence={"off_camera_gaze_share": v, "median": med, "robust_z": round(z, 3), "direction": direction, **source_span(turn, i)},
                    cue=f"Off-camera gaze was {direction} than baseline; consider cultural norms, comfort, and question context.",
                    turn_index=i,
                ))
        return result


class OffCameraGazeFrequencyObserver:
    """Off-camera gaze frequency: share of turns with elevated off-camera gaze.

    Distinct from GazePatternObserver (per-turn robust-z shift): this is
    a session-level frequency — how often gaze was directed off-camera
    across the interview. Emits one observation anchored at the last
    elevated turn when >=3 turns carry the feature and >=40% are
    elevated (>=0.5). Wording is always "off-camera gaze".
    """

    method_id = "cueliez.observations.visual.off_camera_gaze_frequency/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "off_camera_gaze_share", "gaze_aversion_ratio", "gaze_away_ratio", "averted_gaze_ratio")
            if v is not None and 0 <= v <= 1:
                vals.append((i, v, turn))
        if len(vals) < 3:
            result.notes.append("insufficient_off_camera_gaze_data")
            return result
        elevated = [(i, v, t) for i, v, t in vals if v >= 0.5]
        freq = len(elevated) / len(vals)
        if freq < 0.4 or not any(v >= 0.6 for _, v, _ in elevated):
            return result
        score = clamp01(0.35 + 0.30 * freq)
        last_i, _last_v, last_turn = elevated[-1]
        ev: Dict[str, Any] = {
            "off_camera_gaze_frequency": round(freq, 3),
            "elevated_turn_count": len(elevated),
            "sample_count": len(vals),
            "max_off_camera_gaze_share": round(max(v for _, v, _ in vals), 3),
        }
        ev.update(source_span(last_turn, last_i))
        result.observations.append(make_observation(
            label="off_camera_gaze_frequency_elevated",
            score=score,
            method_id=self.method_id,
            category="visual",
            evidence=ev,
            cue="Off-camera gaze was frequent across this session relative to the turns measured; consider cultural norms, comfort, and camera position.",
            turn_index=last_i,
        ))
        return result


class BlinkRateTrendObserver:
    """Blink-rate trend shift: early vs late session halves."""

    method_id = "cueliez.observations.visual.blink_rate_trend/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            v = _feat(turn, "blink_rate_per_min", "blink_rate", "blinks_per_minute")
            if v is not None and 0 <= v <= 120:
                vals.append((i, v, turn))
        if len(vals) < 4:
            result.notes.append("insufficient_blink_trend_data")
            return result
        half = len(vals) // 2
        em = statistics.median([v for _, v, _ in vals[:half]])
        lm = statistics.median([v for _, v, _ in vals[half:]])
        if em == 0:
            return result
        rel = (lm - em) / abs(em)
        if abs(rel) < 0.30:
            return result
        direction = "higher" if lm > em else "lower"
        score = clamp01(0.36 + min(abs(rel), 1.5) * 0.22)
        anchor_i, _anchor_v, anchor_turn = vals[-1]
        ev = {
            "early_median_blinks_per_min": round(em, 2),
            "late_median_blinks_per_min": round(lm, 2),
            "relative_change": round(rel, 3),
            "direction": direction,
            "sample_count": len(vals),
        }
        ev.update(source_span(anchor_turn, anchor_i))
        result.observations.append(make_observation(
            label="blink_rate_trend_shift_observed",
            score=score,
            method_id=self.method_id,
            category="visual",
            evidence=ev,
            cue=f"Blink rate was {direction} in the later part of the session than at the start; interpret only alongside context and other observations.",
            turn_index=vals[-1][0],
        ))
        return result


class RestlessnessShiftObserver:
    """Movement/restlessness trend shift: early vs late session halves.

    Uses the same supplied motor-activity index as MotorActivityObserver
    (gesture + head-movement + posture-shift counts). A sustained rise
    or fall across the session is a cue to consider seating, room
    conditions, and individual baseline — never a finding.
    """

    method_id = "cueliez.observations.visual.restlessness_shift/v1"
    gated_modality = "camera"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        vals: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            g = _feat(turn, "gesture_count", "hand_movement_events")
            h = _feat(turn, "head_movement_events", "head_motion_events")
            p = _feat(turn, "posture_shift_count", "posture_shifts")
            parts = [x for x in (g, h, p) if x is not None and x >= 0]
            if parts:
                vals.append((i, sum(parts), turn))
        if len(vals) < 4:
            result.notes.append("insufficient_restlessness_data")
            return result
        half = len(vals) // 2
        em = statistics.median([v for _, v, _ in vals[:half]])
        lm = statistics.median([v for _, v, _ in vals[half:]])
        if em == 0:
            if lm == 0:
                return result
            rel = 1.0
        else:
            rel = (lm - em) / abs(em)
        if abs(rel) < 0.40:
            return result
        direction = "higher" if lm > em else "lower"
        score = clamp01(0.36 + min(abs(rel), 1.5) * 0.22)
        anchor_i, _anchor_v, anchor_turn = vals[-1]
        ev = {
            "early_median_activity_index": round(em, 2),
            "late_median_activity_index": round(lm, 2),
            "relative_change": round(rel, 3),
            "direction": direction,
            "sample_count": len(vals),
        }
        ev.update(source_span(anchor_turn, anchor_i))
        result.observations.append(make_observation(
            label="movement_restlessness_shift_observed",
            score=score,
            method_id=self.method_id,
            category="visual",
            evidence=ev,
            cue=f"Observed movement was {direction} in the later part of the session than at the start; consider environment and individual baseline.",
            turn_index=vals[-1][0],
        ))
        return result


class BlinkRateObserver:
    method_id = "cueliez.observations.visual.blink_rate/v1"
    gated_modality = "camera"

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
    gated_modality = "camera"

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
