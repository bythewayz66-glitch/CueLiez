"""Behavioral-pattern observation methods from structured interview data.

These operate on transcript/turn metadata (timing, lengths, turn structure), not
raw biometrics. They emit cues for human review, never verdicts.
"""

from __future__ import annotations

import re
import statistics
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, text_of

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


def _num(turn: Mapping[str, Any], *keys: str) -> float | None:
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
        latencies: list[tuple[int, float]] = []
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            lat = _num(turn, "response_latency_ms", "latency_ms", "delay_ms")
            if lat is None:
                lat_s = _num(turn, "response_latency_s", "latency_s", "delay_s")
                if lat_s is not None:
                    lat = lat_s * 1000.0
            if lat is not None and lat >= 0:
                latencies.append((i, lat))
        if len(latencies) < 3:
            result.notes.append("insufficient_latency_data")
            return result
        vals = [v for _, v in latencies]
        med = statistics.median(vals)
        mad = statistics.median([abs(v - med) for v in vals]) or 1.0
        for i, v in latencies:
            z = (v - med) / (1.4826 * mad)
            if abs(z) >= 2.0 and v >= 1500:
                score = clamp01(0.4 + min(abs(z), 6.0) * 0.08)
                direction = "longer" if v > med else "shorter"
                result.observations.append(make_observation(
                    label="response_latency_anomaly_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence={"latency_ms": v, "median_ms": med, "robust_z": round(z, 3), "direction": direction},
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
        if len(lens) < 4:
            return result
        vals = [w for _, w, _ in lens]
        mean = statistics.mean(vals)
        stdev = statistics.pstdev(vals) or 1.0
        for i, wc, ex in lens:
            if wc <= 3 and mean >= 12:
                z = (mean - wc) / stdev
                if z >= 1.5:
                    score = clamp01(0.35 + min(z, 5.0) * 0.08)
                    result.observations.append(make_observation(
                        label="notably_brief_response_observed",
                        score=score,
                        method_id=self.method_id,
                        category="behavioral",
                        evidence={"word_count": wc, "session_mean_words": round(mean, 2), "z": round(z, 3), "excerpt": ex},
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
            score = clamp01(0.45 + 0.1 * min(len(found), 4))
            result.observations.append(make_observation(
                label="question_deflection_markers_present",
                score=score,
                method_id=self.method_id,
                category="behavioral",
                evidence={"patterns": found[:8], "excerpt": text[:180]},
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
                result.observations.append(make_observation(
                    label="speech_rate_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="behavioral",
                    evidence={"wpm": round(wpm, 2), "median_wpm": round(med, 2), "robust_z": round(z, 3), "direction": direction},
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
            result.observations.append(make_observation(
                label="filled_pause_markers_elevated",
                score=score,
                method_id=self.method_id,
                category="behavioral",
                evidence={"filled_pause_count": total, "word_count": words, "rate": round(rate, 4)},
                cue="Filled pauses/disfluency markers were elevated; allow time and ask clear, focused questions.",
                turn_index=i,
            ))
        return result


class InterruptionOverlapObserver:
    method_id = "cueliez.observations.behavioral.interruption_overlap/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            interrupted = turn.get("interrupted") is True or (_num(turn, "overlap_ms") or 0) > 150
            overlap = _num(turn, "overlap_ms")
            if not interrupted:
                continue
            score = clamp01(0.45 + min((overlap or 200) / 2000.0, 0.35))
            ev: dict[str, Any] = {"interrupted": True}
            if overlap is not None:
                ev["overlap_ms"] = overlap
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
