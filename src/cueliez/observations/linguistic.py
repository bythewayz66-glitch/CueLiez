"""Linguistic observation methods.

Heuristic, text-based indicators for interview review. Outputs are cues, not
verdicts. Confidence reflects strength/presence of the pattern in the text.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, text_of

_WORD_RE = re.compile(r"[A-Za-z']+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _count_patterns(text: str, patterns: Sequence[str]) -> tuple[int, list[str]]:
    found: list[str] = []
    total = 0
    low = text.lower()
    for p in patterns:
        n = len(re.findall(p, low))
        if n:
            total += n
            found.append(p)
    return total, found


HEDGE_PATTERNS = [
    r"\bmaybe\b", r"\bperhaps\b", r"\bpossibly\b", r"\bprobably\b",
    r"\bi think\b", r"\bi guess\b", r"\bi believe\b", r"\bi suppose\b",
    r"\bsort of\b", r"\bkind of\b", r"\bkinda\b", r"\bsorta\b",
    r"\babout\b", r"\baround\b", r"\broughly\b", r"\bapproximately\b",
    r"\bi don't recall\b", r"\bi don't remember\b", r"\bi can't recall\b",
    r"\bnot sure\b", r"\bif i recall\b", r"\bas far as i know\b",
    r"\bto the best of my\b", r"\bi might be wrong\b",
]

DISTANCING_PATTERNS = [
    r"\bthat (?:guy|man|woman|person|individual)\b",
    r"\bthe (?:vehicle|car|item|object|weapon)\b",
    r"\bone\b(?:\s+(?:would|could|might|should)\b)",
    r"\bpeople\b", r"\bsomeone\b", r"\ba person\b",
    r"\bthose (?:people|things|guys)\b",
]

DENIAL_PATTERNS = [
    r"\bi did not\b", r"\bi didn't\b", r"\bnever\b", r"\bno way\b",
    r"\babsolutely not\b", r"\bi swear\b", r"\bi promise\b",
    r"\bto be honest\b", r"\bhonestly\b", r"\btruthfully\b",
    r"\bi would never\b", r"\bthat's not true\b", r"\bi'm telling you\b",
]

VAGUE_PATTERNS = [
    r"\bstuff\b", r"\bthings\b", r"\bsomething\b", r"\bwhatever\b",
    r"\betc\b", r"\band so on\b", r"\blike that\b", r"\byou know\b",
    r"\ba while\b", r"\bsome time\b", r"\blater\b", r"\bearlier\b",
    r"\bsomewhere\b", r"\bsomehow\b",
]

# Discourse fillers are common; treat as weak vagueness unless paired with stronger vague referents.
_WEAK_VAGUE_PATTERNS = frozenset({r"\byou know\b", r"\blike that\b"})

CERTAINTY_HIGH = [r"\bdefinitely\b", r"\bcertainly\b", r"\babsolutely\b", r"\bclearly\b", r"\bno doubt\b", r"\balways\b", r"\bpositive\b", r"\b100%\b"]
CERTAINTY_LOW = [r"\bmaybe\b", r"\bpossibly\b", r"\bnot sure\b", r"\bi think\b", r"\bmight\b", r"\bcould\b", r"\bunsure\b"]

MINIMIZATION_PATTERNS = [
    r"\bjust\b", r"\bonly\b", r"\ba little\b", r"\bnot that\b",
    r"\bno big deal\b", r"\bit was nothing\b", r"\bbarely\b",
    r"\bmerely\b", r"\bminor\b",
]

PASSIVE_VOICE_PATTERNS = [
    r"\b(?:was|were|been|being)\s+\w+ed\b",
    r"\b(?:was|were|been)\s+\w+en\b",
    r"\bgot\s+\w+(?:ed|en)\b",
    r"\bit happened\b", r"\bmistakes were made\b",
]

OVERJUSTIFICATION_PATTERNS = [
    r"\bthe reason (?:is|was|why)\b", r"\bbecause\b.*\bbecause\b",
    r"\blet me explain\b", r"\bwhat happened was\b",
    r"\bi mean\b.*\bi mean\b", r"\bsee,?\s+what\b",
]

MEMORY_QUALIFIER_PATTERNS = [
    r"\bif i remember (?:correctly|right)\b", r"\bfrom what i recall\b",
    r"\bi can't remember (?:exactly|clearly)\b", r"\bit's fuzzy\b",
    r"\bi don't recall (?:exactly|the details)\b",
]


class HedgingObserver:
    method_id = "cueliez.observations.linguistic.hedging/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 4:
                continue
            count, found = _count_patterns(text, HEDGE_PATTERNS)
            if not count:
                continue
            # Precision: a single weak hedge in short/normal text is common; require stronger evidence.
            if count < 2 and len(words) < 10:
                continue
            rate = count / max(1, len(words))
            score = clamp01(0.30 + min(rate, 0.35) * 2.2 + min(count, 6) * 0.06)
            if score < 0.36:
                continue
            result.observations.append(make_observation(
                label="hedging_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={
                    "hedge_count": count,
                    "distinct_pattern_groups": len(found),
                    "word_count": len(words),
                    "hedge_rate": round(rate, 4),
                    "patterns_matched": found[:8],
                },
                cue="Response includes hedging/qualification language; consider asking for specific details.",
                turn_index=i,
            ))
        return result


class PronounDistancingObserver:
    method_id = "cueliez.observations.linguistic.pronoun_distancing/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 5:
                continue
            i_count = len(re.findall(r"\b(i|me|my|mine|we|our|us)\b", text.lower()))
            dist_count, found = _count_patterns(text, DISTANCING_PATTERNS)
            if dist_count == 0:
                continue
            # Generic third-person references are common; require multiple markers or clear distancing context.
            generic_only = found and all(p in (r"\bpeople\b", r"\bsomeone\b", r"\ba person\b") for p in found)
            if generic_only and dist_count < 2:
                continue
            ratio = dist_count / max(1, i_count + dist_count)
            score = clamp01(0.22 + min(dist_count, 5) * 0.10 + ratio * 0.32)
            if score < 0.34:
                continue
            result.observations.append(make_observation(
                label="distancing_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={
                    "distancing_count": dist_count,
                    "first_person_count": i_count,
                    "distancing_ratio": round(ratio, 4),
                    "patterns_matched": found[:8],
                },
                cue="Language shows distancing from people/objects/events; consider probing ownership and direct involvement.",
                turn_index=i,
            ))
        return result


class NegationDensityObserver:
    method_id = "cueliez.observations.linguistic.negation_density/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 6:
                continue
            count, found = _count_patterns(text, DENIAL_PATTERNS)
            if not count:
                continue
            rate = count / max(1, len(words))
            score = clamp01(0.3 + count * 0.1 + rate * 5.0)
            if score < 0.35:
                continue
            result.observations.append(make_observation(
                label="denial_or_emphatic_negation_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={"count": count, "word_count": len(words), "rate": round(rate, 4), "patterns": found[:8]},
                cue="Response contains emphatic negation/assurance language; focus on verifiable details rather than assurances.",
                turn_index=i,
            ))
        return result


class DetailVaguenessObserver:
    method_id = "cueliez.observations.linguistic.detail_vagueness/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 8:
                continue
            vague_count, found = _count_patterns(text, VAGUE_PATTERNS)
            if not vague_count:
                continue
            strong_found = [p for p in found if p not in _WEAK_VAGUE_PATTERNS]
            weak_only = bool(found) and not strong_found
            if weak_only and vague_count < 2:
                continue
            numbers = len(re.findall(r"\b\d+(?:[:/.-]\d+)?\b", text))
            caps = len(re.findall(r"\b[A-Z][a-z]{2,}\b", text))
            specificity = numbers + max(0, caps - 1) * 0.5
            effective_vague = vague_count - (0.5 * sum(1 for p in found if p in _WEAK_VAGUE_PATTERNS))
            rate = effective_vague / max(1, len(words))
            score = clamp01(0.18 + effective_vague * 0.09 + rate * 4.0 - min(specificity, 5) * 0.07)
            if score < 0.36:
                continue
            result.observations.append(make_observation(
                label="low_specificity_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={
                    "vague_marker_count": vague_count,
                    "effective_vague_score": round(effective_vague, 2),
                    "strong_vague_patterns": strong_found[:8],
                    "specificity_proxy": round(specificity, 2),
                    "word_count": len(words),
                    "patterns_matched": found[:8],
                },
                cue="Account uses general/vague references; ask for who/what/when/where specifics.",
                turn_index=i,
            ))
        return result


class CertaintySwingObserver:
    method_id = "cueliez.observations.linguistic.certainty_swing/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        subject_turns = [(i, text_of(t)) for i, t in enumerate(transcript) if is_subject_turn(t) and text_of(t).strip()]
        if len(subject_turns) < 2:
            return result
        prev_mode = None
        prev_hi = 0
        prev_lo = 0
        prev_i = None
        for i, text in subject_turns:
            hi, _ = _count_patterns(text, CERTAINTY_HIGH)
            lo, _ = _count_patterns(text, CERTAINTY_LOW)
            if hi == 0 and lo == 0:
                continue
            mode = "high" if hi > lo else ("low" if lo > hi else prev_mode or "high")
            if mode not in ("high", "low"):
                mode = "high" if hi >= lo else "low"
            if prev_mode and mode != prev_mode:
                # Precision: require some marker strength on at least one side of the swing.
                if max(prev_hi, prev_lo, hi, lo) < 1 or (prev_hi + prev_lo + hi + lo) < 2:
                    prev_mode, prev_hi, prev_lo, prev_i = mode, hi, lo, i
                    continue
                strength = min(prev_hi + prev_lo + hi + lo, 6)
                score = clamp01(0.40 + 0.08 * strength)
                result.observations.append(make_observation(
                    label="certainty_shift_across_turns",
                    score=score,
                    method_id=self.method_id,
                    category="linguistic",
                    evidence={
                        "from_mode": prev_mode,
                        "to_mode": mode,
                        "from_turn_index": prev_i,
                        "to_turn_index": i,
                        "from_high_markers": prev_hi,
                        "from_low_markers": prev_lo,
                        "to_high_markers": hi,
                        "to_low_markers": lo,
                    },
                    cue="Certainty level shifted across responses; clarify what is known directly vs inferred.",
                    turn_index=i,
                ))
            prev_mode, prev_hi, prev_lo, prev_i = mode, hi, lo, i
        return result


class MinimizationObserver:
    method_id = "cueliez.observations.linguistic.minimization/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 5:
                continue
            count, found = _count_patterns(text, MINIMIZATION_PATTERNS)
            # "just"/"only" are common; require density or co-occurrence.
            if count < 2 and not any(p for p in found if p not in (r"\bjust\b", r"\bonly\b")):
                continue
            rate = count / max(1, len(words))
            score = clamp01(0.25 + count * 0.08 + rate * 3.5)
            if score < 0.35:
                continue
            result.observations.append(make_observation(
                label="minimizing_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={
                    "minimizer_count": count,
                    "word_count": len(words),
                    "minimizer_rate": round(rate, 4),
                    "patterns_matched": found[:8],
                },
                cue="Response uses minimizing language; probe the full scope and impact of events.",
                turn_index=i,
            ))
        return result


class PassiveVoiceProxyObserver:
    method_id = "cueliez.observations.linguistic.passive_voice_proxy/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 8:
                continue
            count, found = _count_patterns(text, PASSIVE_VOICE_PATTERNS)
            if count < 2:
                continue
            rate = count / max(1, len(words))
            score = clamp01(0.3 + count * 0.08 + rate * 3.0)
            result.observations.append(make_observation(
                label="agentless_or_passive_constructions_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={"count": count, "rate": round(rate, 4), "patterns": found[:6]},
                cue="Account uses passive/agentless constructions; ask who performed key actions.",
                turn_index=i,
            ))
        return result


class OverjustificationObserver:
    method_id = "cueliez.observations.linguistic.overjustification/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 15:
                continue
            count, found = _count_patterns(text, OVERJUSTIFICATION_PATTERNS)
            if not count:
                continue
            # Long response with justification markers can indicate over-explaining; cue only.
            length_factor = min(len(words), 120) / 120.0
            score = clamp01(0.25 + count * 0.18 + length_factor * 0.2)
            if score < 0.38:
                continue
            result.observations.append(make_observation(
                label="extended_justification_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={
                    "justification_marker_count": count,
                    "word_count": len(words),
                    "patterns_matched": found[:6],
                },
                cue="Response includes extended justification; separate core facts from explanations and verify key points.",
                turn_index=i,
            ))
        return result


class MemoryQualifierObserver:
    method_id = "cueliez.observations.linguistic.memory_qualifiers/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        for i, turn in enumerate(transcript):
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 5:
                continue
            count, found = _count_patterns(text, MEMORY_QUALIFIER_PATTERNS)
            if not count:
                continue
            score = clamp01(0.4 + count * 0.15)
            result.observations.append(make_observation(
                label="memory_qualification_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence={"count": count, "patterns": found[:6]},
                cue="Response qualifies memory/certainty; distinguish direct recall from reconstruction.",
                turn_index=i,
            ))
        return result
