"""Behavioral-pattern observation methods from structured interview data.

These operate on transcript/turn metadata (timing, lengths, turn structure), not
raw biometrics. They emit cues for human review, never verdicts.
"""

from __future__ import annotations

import re
import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, source_span, text_of, truncate_source
from .thresholds import (
    BRIEF_RESPONSE_MAX_WORDS,
    BRIEF_RESPONSE_MEAN_MIN,
    BRIEF_RESPONSE_MIN_SAMPLES,
    BRIEF_RESPONSE_Z,
    INTERRUPTION_OVERLAP_MS,
    LATENCY_ANOMALY_Z,
    LATENCY_MIN_MS,
    LATENCY_MIN_SAMPLES,
)

_EVASION_PATTERNS = [
    r"\bwhy (?:do|would) you ask\b",
    r"\bthat'?s not relevant\b",
    r"\bcan we talk about\b",
    r"\bi already told you\b",
    r"\bwhat do you mean\b",
    r"\byou know what i mean\b",
    r"\blet'?s move on\b",
    r"\bi don't want to (?:talk|answer|discuss)\b",
    r"\bi refuse to\b",
]

_FILLER_RE = re.compile(r"\b(um+|uh+|er+|ah+|hmm+|mm+)\b", re.I)


def _num(turn: Any, *keys: str) -> float | None:
    if not isinstance(turn, Mapping):
        return None
    for k in keys:
        v = turn.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    meta = turn.get("meta") or turn.get("metadata") or {}
    if isinstance(meta, Mapping):
        for k in keys:
            v = meta.get(k)
            if isinstance(v, (int, float)):
                return float(v)
    return None


class ResponseLatencyObserver:
    method_id = "cueliez.observations.behavioral.response_latency/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        latencies: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            lat = _num(turn, "response_latency_ms", "latency_ms", "delay_ms")
            if lat is None:
                lat_s = _num(turn, "response_latency_s", "latency_s", "delay_s")
                if lat_s is not None:
                    lat = lat_s * 1000.0
            if lat is not None and lat >= 0:
                latencies.append((i, lat, turn))
        if len(latencies) < LATENCY_MIN_SAMPLES:
            result.notes.append("insufficient_latency_data")
            return result
        vals = [v for _, v, _ in latencies]
        med = statistics.median(vals)
        mad = statistics.median([abs(v - med) for v in vals]) or 1.0
        for i, v, turn in latencies:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= LATENCY_ANOMALY_Z and v >= LATENCY_MIN_MS:
                score = clamp01(0.4 + min(abs(z), 6.0) * 0.08)
                direction = "longer" if v > med else "shorter"
                ev = {
                    "latency_ms": round(v, 2),
                    "baseline_median_ms": round(med, 2),
                    "robust_z": round(z, 3),
                    "direction": direction,
                    "sample_count": len(latencies),
                }
                ev.update(source_span(turn, i))
                result.observations.append(make_observation(
                    label="response_latency_anomaly_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence=ev,
                    cue=f"Response latency was notably {direction} than this session's baseline; consider context and question complexity.",
                    turn_index=i,
                ))
        return result


class AnswerLengthVarianceObserver:
    method_id = "cueliez.observations.behavioral.answer_length_variance/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        lens: list[tuple[int, int, str]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn).strip()
            if not text:
                continue
            wc = len(re.findall(r"[A-Za-z']+", text))
            lens.append((i, wc, text[:160]))
        if len(lens) < BRIEF_RESPONSE_MIN_SAMPLES:
            return result
        vals = [w for _, w, _ in lens]
        mean = statistics.mean(vals)
        stdev = statistics.pstdev(vals) or 1.0
        for i, wc, ex in lens:
            if wc <= BRIEF_RESPONSE_MAX_WORDS and mean >= BRIEF_RESPONSE_MEAN_MIN:
                z = (mean - wc) / stdev
                if z >= BRIEF_RESPONSE_Z:
                    score = clamp01(0.35 + min(z, 5.0) * 0.08)
                    result.observations.append(make_observation(
                        label="notably_brief_response_observed",
                        score=score,
                        method_id=self.method_id,
                        category="behavioral",
                        evidence={
                            "word_count": wc,
                            "session_mean_words": round(mean, 2),
                            "session_stdev_words": round(stdev, 2),
                            "z_score": round(z, 3),
                            "sample_count": len(lens),
                            "excerpt": ex,
                            "turn_index": i,
                            "source_text": truncate_source(ex),
                        },
                        cue="Response was markedly brief relative to the session; ask an open follow-up for detail.",
                        turn_index=i,
                    ))
        return result


class EvasionMarkerObserver:
    method_id = "cueliez.observations.behavioral.evasion_markers/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            if len(text.strip()) < 4:
                continue
            found = [p for p in _EVASION_PATTERNS if re.search(p, text.lower())]
            if not found:
                continue
            score = clamp01(0.42 + 0.09 * min(len(found), 4))
            ev = {
                "matched_pattern_count": len(found),
                "patterns_matched": found[:8],
                "excerpt": text[:180],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="question_deflection_markers_present",
                score=score,
                method_id=self.method_id,
                category="behavioral",
                evidence=ev,
                cue="Response includes deflection/avoidance phrasing; restate the question and request a direct answer.",
                turn_index=i,
            ))
        return result


class SpeechRateShiftObserver:
    method_id = "cueliez.observations.behavioral.speech_rate_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        rates: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            wc = len(re.findall(r"[A-Za-z']+", text))
            dur = _num(turn, "duration_ms", "speech_duration_ms")
            if dur is None:
                dur_s = _num(turn, "duration_s", "speech_duration_s")
                if dur_s is not None:
                    dur = dur_s * 1000.0
            if wc >= 3 and dur and dur > 250:
                wpm = wc / (dur / 60000.0)
                if 30 <= wpm <= 400:
                    rates.append((i, wpm))
        if len(rates) < 3:
            result.notes.append("insufficient_speech_rate_data")
            return result
        vals = [v for _, v in rates]
        med = statistics.median(vals)
        mad = statistics.median([abs(v - med) for v in vals]) or 1.0
        for i, wpm in rates:
            z = (wpm - med) / (1.4826 * mad)
            if abs(z) >= 2.0:
                score = clamp01(0.38 + min(abs(z), 6.0) * 0.08)
                direction = "faster" if wpm > med else "slower"
                ev = {
                    "wpm": round(wpm, 2),
                    "baseline_median_wpm": round(med, 2),
                    "robust_z": round(z, 3),
                    "direction": direction,
                    "sample_count": len(rates),
                }
                _turn = transcript[i] if 0 <= i < len(transcript) else {}
                ev.update(source_span(_turn, i))
                result.observations.append(make_observation(
                    label="speech_rate_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence=ev,
                    cue=f"Speech rate was notably {direction} than baseline; consider cognitive load or topic sensitivity.",
                    turn_index=i,
                ))
        return result


class FilledPauseMarkerObserver:
    method_id = "cueliez.observations.behavioral.filled_pauses/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        counts: list[tuple[int, int, int]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = len(re.findall(r"[A-Za-z']+", text))
            if words < 4:
                continue
            meta_count = _num(turn, "filler_count", "filled_pauses", "filled_pause_count")
            text_count = len(_FILLER_RE.findall(text))
            total = int(meta_count) if meta_count is not None else text_count
            counts.append((i, total, words))
        if not counts:
            return result
        for i, total, words in counts:
            if total < 2:
                continue
            rate = total / max(1, words)
            score = clamp01(0.3 + total * 0.08 + rate * 2.0)
            if score < 0.36:
                continue
            ev = {
                "filled_pause_count": total,
                "word_count": words,
                "disfluency_rate": round(rate, 4),
                "source": "metadata" if meta_count is not None else "text_markers",
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="filled_pause_markers_elevated",
                score=score,
                method_id=self.method_id,
                category="behavioral",
                evidence=ev,
                cue="Filled pauses/disfluency markers were elevated; allow time and ask clear, focused questions.",
                turn_index=i,
            ))
        return result


def _early_late_shift(values: list[tuple[int, float]]) -> tuple[float, float, float] | None:
    """Median of the first half vs the second half of a per-turn series.

    Returns (early_median, late_median, relative_change) or None when
    there are too few samples. Relative change is vs the early median.
    """
    if len(values) < 4:
        return None
    half = len(values) // 2
    early = [v for _, v in values[:half]]
    late = [v for _, v in values[half:]]
    if not early or not late:
        return None
    em, lm = statistics.median(early), statistics.median(late)
    if em == 0:
        return None
    return em, lm, (lm - em) / abs(em)


class ResponseLatencyShiftObserver:
    """Response-latency trend shift: early vs late session halves.

    Distinct from ResponseLatencyObserver (per-turn robust-z anomaly):
    this compares the median latency of the first half of subject turns
    with the median of the second half. A large sustained shift is a cue
    to consider fatigue, topic change, or question difficulty. Cue only.
    """

    method_id = "cueliez.observations.behavioral.response_latency_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        latencies: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            lat = _num(turn, "response_latency_ms", "latency_ms", "delay_ms")
            if lat is None:
                lat_s = _num(turn, "response_latency_s", "latency_s", "delay_s")
                if lat_s is not None:
                    lat = lat_s * 1000.0
            if lat is not None and lat >= 0:
                latencies.append((i, lat, turn))
        shift = _early_late_shift([(i, v) for i, v, _ in latencies])
        if shift is None:
            result.notes.append("insufficient_latency_shift_data")
            return result
        em, lm, rel = shift
        if abs(rel) < 0.40 or abs(lm - em) < 500:
            return result
        direction = "longer" if lm > em else "shorter"
        score = clamp01(0.38 + min(abs(rel), 1.5) * 0.25)
        anchor_i, _anchor_v, anchor_turn = latencies[-1]
        ev = {
            "early_median_ms": round(em, 2),
            "late_median_ms": round(lm, 2),
            "relative_change": round(rel, 3),
            "direction": direction,
            "sample_count": len(latencies),
        }
        ev.update(source_span(anchor_turn, anchor_i))
        result.observations.append(make_observation(
            label="response_latency_shift_across_turns",
            score=score,
            method_id=self.method_id,
            category="behavioral",
            evidence=ev,
            cue=f"Response latency was {direction} in the later part of the session than at the start; consider fatigue, topic change, or question difficulty.",
            turn_index=latencies[-1][0],
        ))
        return result


class SpeechRateTrendObserver:
    """Speech-rate trend shift: early vs late session halves (wpm)."""

    method_id = "cueliez.observations.behavioral.speech_rate_trend/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        rates: list[tuple[int, float, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            wc = len(re.findall(r"[A-Za-z']+", text))
            dur = _num(turn, "duration_ms", "speech_duration_ms")
            if dur is None:
                dur_s = _num(turn, "duration_s", "speech_duration_s")
                if dur_s is not None:
                    dur = dur_s * 1000.0
            if wc >= 3 and dur and dur > 250:
                wpm = wc / (dur / 60000.0)
                if 30 <= wpm <= 400:
                    rates.append((i, wpm, turn))
        shift = _early_late_shift([(i, v) for i, v, _ in rates])
        if shift is None:
            result.notes.append("insufficient_speech_rate_trend_data")
            return result
        em, lm, rel = shift
        if abs(rel) < 0.25:
            return result
        direction = "faster" if lm > em else "slower"
        score = clamp01(0.36 + min(abs(rel), 1.5) * 0.25)
        anchor_i, _anchor_v, anchor_turn = rates[-1]
        ev = {
            "early_median_wpm": round(em, 2),
            "late_median_wpm": round(lm, 2),
            "relative_change": round(rel, 3),
            "direction": direction,
            "sample_count": len(rates),
        }
        ev.update(source_span(anchor_turn, anchor_i))
        result.observations.append(make_observation(
            label="speech_rate_trend_shift_observed",
            score=score,
            method_id=self.method_id,
            category="behavioral",
            evidence=ev,
            cue=f"Speech rate was {direction} in the later part of the session than at the start; consider cognitive load or topic sensitivity.",
            turn_index=rates[-1][0],
        ))
        return result


class FilledPauseClusterObserver:
    """Filled-pause clusters: >=3 in one turn, or in consecutive turns.

    Distinct from FilledPauseMarkerObserver (per-turn elevation): a
    cluster is several filled pauses packed into one response, or
    disfluency persisting across back-to-back responses. Cue only.
    """

    method_id = "cueliez.observations.behavioral.filled_pause_cluster/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        counts: list[tuple[int, int, int, Any]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = len(re.findall(r"[A-Za-z']+", text))
            if words < 4:
                continue
            meta_count = _num(turn, "filler_count", "filled_pauses", "filled_pause_count")
            text_count = len(_FILLER_RE.findall(text))
            total = int(meta_count) if meta_count is not None else text_count
            counts.append((i, total, words, turn))
        if not counts:
            return result
        emitted: set[int] = set()
        for idx, (i, total, words, turn) in enumerate(counts):
            if total >= 3 and i not in emitted:
                score = clamp01(0.40 + 0.07 * min(total, 8))
                ev = {
                    "filled_pause_count": total,
                    "word_count": words,
                    "cluster_kind": "single_turn",
                }
                ev.update(source_span(turn, i))
                result.observations.append(make_observation(
                    label="filled_pause_cluster_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence=ev,
                    cue="Several filled pauses clustered in one response; allow time and ask clear, focused questions.",
                    turn_index=i,
                ))
                emitted.add(i)
        for idx in range(len(counts) - 1):
            i0, c0, _, t0 = counts[idx]
            i1, c1, _, t1 = counts[idx + 1]
            if c0 >= 2 and c1 >= 2 and i1 == i0 + 1 and i1 not in emitted:
                score = clamp01(0.40 + 0.05 * min(c0 + c1, 10))
                ev = {
                    "filled_pause_counts": [c0, c1],
                    "turn_indices": [i0, i1],
                    "cluster_kind": "consecutive_turns",
                    "source_texts": [source_span(t0, i0), source_span(t1, i1)],
                }
                ev.update(source_span(t1, i1))
                result.observations.append(make_observation(
                    label="filled_pause_cluster_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence=ev,
                    cue="Filled pauses persisted across consecutive responses; allow time and ask clear, focused questions.",
                    turn_index=i1,
                ))
                emitted.add(i1)
        return result


class InterruptionOverlapObserver:
    method_id = "cueliez.observations.behavioral.interruption_overlap/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            interrupted_flag = turn.get("interrupted") is True if isinstance(turn, Mapping) else False
            interrupted = interrupted_flag or (_num(turn, "overlap_ms") or 0) > INTERRUPTION_OVERLAP_MS
            overlap = _num(turn, "overlap_ms")
            if not interrupted:
                continue
            score = clamp01(0.45 + min((overlap or 200) / 2000.0, 0.35))
            ev: dict[str, Any] = {"interrupted": True, "source": "overlap_ms" if overlap is not None else "interrupted_flag"}
            if overlap is not None:
                ev["overlap_ms"] = round(overlap, 2)
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="turn_overlap_or_interruption_observed",
                score=score,
                method_id=self.method_id,
                category="behavioral",
                evidence=ev,
                cue="Turn overlap/interruption occurred; ensure the subject had opportunity to complete their account.",
                turn_index=i,
            ))
        return result
