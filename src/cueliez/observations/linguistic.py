"""Linguistic observation methods.

Heuristic, text-based indicators for interview review. Outputs are cues, not
verdicts. Confidence reflects strength/presence of the pattern in the text.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, source_span, text_of
from .thresholds import HEDGING_EMIT_SCORE, HEDGING_MIN_COUNT_OR_LONG, HEDGING_MIN_WORDS

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

# Approximation tokens that are often ordinary time approximations (not hedging evasiveness)
# when immediately followed by a time expression. Exclude only those contextual occurrences.
_TIME_APPROX_HEDGE_PATTERNS = (r"\babout\b", r"\baround\b", r"\broughly\b", r"\bapproximately\b")
_TIME_EXPR_AFTER_APPROX = re.compile(
    r"\s+(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
    r"|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|noon|midnight)"
    r"(?:[\s-]*(?:o['’]?clock|thirty|fifteen|forty[- ]five|ten|twenty|oh\s*\d))?\b",
    re.I,
)


def _hedge_count_adjusted(text: str) -> tuple[int, list[str]]:
    """Count hedge patterns, excluding time-approximation tokens used as clock-time approximations."""
    low = text.lower()
    count, found = _count_patterns(text, HEDGE_PATTERNS)
    if not count:
        return 0, []
    # Remove contextual time-approximation matches (e.g., "around nine-thirty") from hedging evidence.
    approx_removed = 0
    remaining_found = list(found)
    for pat in _TIME_APPROX_HEDGE_PATTERNS:
        if pat not in remaining_found:
            continue
        removed_for_pat = 0
        for m in re.finditer(pat, low):
            tail = low[m.end() :]
            if _TIME_EXPR_AFTER_APPROX.match(tail):
                removed_for_pat += 1
        if removed_for_pat:
            n = len(re.findall(pat, low))
            approx_removed += removed_for_pat
            if removed_for_pat >= n and pat in remaining_found:
                remaining_found.remove(pat)
    adjusted = max(0, count - approx_removed)
    return adjusted, remaining_found


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
            if len(words) < HEDGING_MIN_WORDS:
                continue
            count, found = _hedge_count_adjusted(text)
            if not count:
                continue
            # Precision: a single weak hedge in short/normal text is common; require stronger evidence.
            if count < 2 and len(words) < HEDGING_MIN_COUNT_OR_LONG:
                continue
            rate = count / max(1, len(words))
            score = clamp01(0.30 + min(rate, 0.35) * 2.2 + min(count, 6) * 0.06)
            if score < HEDGING_EMIT_SCORE:
                continue
            ev = {
                "hedge_count": count,
                "distinct_pattern_groups": len(found),
                "word_count": len(words),
                "hedge_rate": round(rate, 4),
                "patterns_matched": found[:8],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="hedging_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "distancing_count": dist_count,
                "first_person_count": i_count,
                "distancing_ratio": round(ratio, 4),
                "patterns_matched": found[:8],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="distancing_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "marker_count": count,
                "word_count": len(words),
                "marker_rate": round(rate, 4),
                "patterns_matched": found[:8],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="denial_or_emphatic_negation_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "vague_marker_count": vague_count,
                "effective_vague_score": round(effective_vague, 2),
                "strong_vague_patterns": strong_found[:8],
                "specificity_proxy": round(specificity, 2),
                "word_count": len(words),
                "patterns_matched": found[:8],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="low_specificity_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
                cue="Account uses general/vague references; ask for who/what/when/where specifics.",
                turn_index=i,
            ))
        return result


class CertaintySwingObserver:
    method_id = "cueliez.observations.linguistic.certainty_swing/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        subject_turns = [(i, t) for i, t in enumerate(transcript) if is_subject_turn(t) and text_of(t).strip()]
        if len(subject_turns) < 2:
            return result
        prev = None  # (mode, hi, lo, i, turn)
        for i, t in subject_turns:
            text = text_of(t)
            hi, _ = _count_patterns(text, CERTAINTY_HIGH)
            lo, _ = _count_patterns(text, CERTAINTY_LOW)
            if hi == 0 and lo == 0:
                continue
            mode = "high" if hi > lo else ("low" if lo > hi else ((prev[0] if prev else "high")))
            if mode not in ("high", "low"):
                mode = "high" if hi >= lo else "low"
            if prev and mode != prev[0]:
                prev_mode, prev_hi, prev_lo, prev_i, prev_t = prev
                # Precision: require some marker strength on at least one side of the swing.
                if max(prev_hi, prev_lo, hi, lo) < 1 or (prev_hi + prev_lo + hi + lo) < 2:
                    prev = (mode, hi, lo, i, t)
                    continue
                strength = min(prev_hi + prev_lo + hi + lo, 6)
                score = clamp01(0.40 + 0.08 * strength)
                ev = {
                    "from_mode": prev_mode,
                    "to_mode": mode,
                    "from_turn_index": prev_i,
                    "to_turn_index": i,
                    "turn_indices": [prev_i, i],
                    "from_high_markers": prev_hi,
                    "from_low_markers": prev_lo,
                    "to_high_markers": hi,
                    "to_low_markers": lo,
                    "source_texts": [source_span(prev_t, prev_i), source_span(t, i)],
                }
                ev.update(source_span(t, i))
                result.observations.append(make_observation(
                    label="certainty_shift_across_turns",
                    score=score,
                    method_id=self.method_id,
                    category="linguistic",
                    evidence=ev,
                    cue="Certainty level shifted across responses; clarify what is known directly vs inferred.",
                    turn_index=i,
                ))
            prev = (mode, hi, lo, i, t)
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
            ev = {
                "minimizer_count": count,
                "word_count": len(words),
                "minimizer_rate": round(rate, 4),
                "patterns_matched": found[:8],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="minimizing_language_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "construction_count": count,
                "word_count": len(words),
                "construction_rate": round(rate, 4),
                "patterns_matched": found[:6],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="agentless_or_passive_constructions_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "justification_marker_count": count,
                "word_count": len(words),
                "patterns_matched": found[:6],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="extended_justification_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
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
            ev = {
                "qualifier_count": count,
                "word_count": len(words),
                "patterns_matched": found[:6],
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="memory_qualification_present",
                score=score,
                method_id=self.method_id,
                category="linguistic",
                evidence=ev,
                cue="Response qualifies memory/certainty; distinguish direct recall from reconstruction.",
                turn_index=i,
            ))
        return result
