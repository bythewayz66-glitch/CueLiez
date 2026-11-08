"""Testimony consistency observation methods.

Heuristic comparison across subject turns. These flag *possible conflicts* for
human review; they do not establish what occurred and are not verdicts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, text_of

_NEG = re.compile(r"\b(no|not|never|didn't|did not|wasn't|was not|isn't|is not|don't|do not|can't|cannot)\b", re.I)
_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b|\b(midnight|noon|morning|afternoon|evening|night)\b", re.I)
_DATEISH_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|tomorrow|last\s+\w+|next\s+\w+)\b", re.I)
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_LOCATION_RE = re.compile(r"\b(?:at|in|to|from|near|inside|outside)\s+([A-Z][A-Za-z0-9'.-]*(?:\s+[A-Z][A-Za-z0-9'.-]*){0,3})")


_NEG_TOKENS = {
    "no", "not", "never", "didnt", "did", "dont", "doesnt", "wasnt", "werent",
    "isnt", "arent", "cant", "cannot", "wont", "wouldnt",
}


def _stem_light(w: str) -> str:
    if len(w) > 5 and w.endswith("ied"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _normalize_claim_key(text: str) -> str:
    t = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    words = []
    for w in t.split():
        if len(w) <= 2:
            continue
        if w in _NEG_TOKENS:
            continue
        if w in {
            "the", "and", "was", "were", "had", "have", "that", "with", "for", "but", "then", "when", "what", "there",
        }:
            continue
        words.append(_stem_light(w))
    return " ".join(words[:8])


def _polarity(text: str) -> int:
    return -1 if _NEG.search(text) else 1


def _subject_turns(transcript: Sequence[Mapping[str, Any]]) -> list[tuple[int, str]]:
    return [(i, text_of(t).strip()) for i, t in enumerate(transcript) if is_subject_turn(t) and text_of(t).strip()]


class ClaimConflictObserver:
    method_id = "cueliez.observations.consistency.claim_conflict/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        buckets: defaultdict[str, list[tuple[int, str, int]]] = defaultdict(list)
        for i, text in _subject_turns(transcript):
            if len(text) < 12:
                continue
            key = _normalize_claim_key(text)
            key_words = key.split()
            if len(key_words) < 2:
                continue
            buckets[key].append((i, text, _polarity(text)))

        for key, items in buckets.items():
            if len(items) < 2:
                continue
            key_words_n = len(key.split())
            # Precision: very short topic keys with only two mentions are often noisy.
            if key_words_n < 3 and len(items) < 3:
                continue
            pols = {p for _, _, p in items}
            if 1 in pols and -1 in pols:
                pos = [it for it in items if it[2] == 1][0]
                neg = [it for it in items if it[2] == -1][0]
                # Confidence reflects topic-key specificity and repeated mentions, not certainty of conflict.
                specificity = min(key_words_n, 8) / 8.0
                score = clamp01(0.46 + specificity * 0.18 + 0.04 * min(len(items), 4))
                result.observations.append(make_observation(
                    label="possible_statement_conflict",
                    score=score,
                    method_id=self.method_id,
                    category="consistency",
                    evidence={
                        "topic_key": key,
                        "topic_key_words": key_words_n,
                        "turn_a": pos[0], "excerpt_a": pos[1][:180], "polarity_a": "affirming",
                        "turn_b": neg[0], "excerpt_b": neg[1][:180], "polarity_b": "negating",
                        "mention_count": len(items),
                    },
                    cue="Statements on a similar topic differ in affirmation/negation; ask the subject to reconcile them.",
                    turn_index=max(pos[0], neg[0]),
                ))
        return result


class TimelineInconsistencyObserver:
    method_id = "cueliez.observations.consistency.timeline_inconsistency/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        mentions: list[tuple[int, list[str], str]] = []
        for i, text in _subject_turns(transcript):
            times = [m.group(0).lower() for m in _TIME_RE.finditer(text)]
            dates = [m.group(0).lower() for m in _DATEISH_RE.finditer(text)]
            refs = times + dates
            if refs:
                mentions.append((i, refs, text[:200]))
        if len(mentions) < 2:
            return result
        clock_times = []
        for i, refs, excerpt in mentions:
            for r in refs:
                if re.search(r"\d", r) and (":" in r or re.search(r"\b(am|pm)\b", r)):
                    clock_times.append((i, r, excerpt))
        uniq = {}
        for i, r, ex in clock_times:
            uniq.setdefault(r, []).append((i, ex))
        if len(uniq) >= 2:
            refs = list(uniq.keys())
            # A single event can legitimately involve multiple times (sequence); emit as a review cue, not inconsistency.
            score = clamp01(0.36 + 0.07 * min(len(refs), 6))
            result.observations.append(make_observation(
                label="multiple_time_references_present",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "distinct_time_refs": refs[:10],
                    "time_reference_count": len(refs),
                    "examples": {k: v[0][0] for k, v in list(uniq.items())[:6]},
                    "note": "Multiple clock times may describe a sequence; verify ordering and consistency with the account.",
                },
                cue="Multiple specific time references appear across responses; verify the sequence and exact times.",
            ))
        return result


class DetailDriftObserver:
    method_id = "cueliez.observations.consistency.detail_drift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        number_sets: list[tuple[int, set[str], str]] = []
        for i, text in _subject_turns(transcript):
            nums = set(_NUMBER_RE.findall(text))
            # Drop trivial small ordinals/counters when other numbers are present to reduce noise.
            nums = {n for n in nums if not (n.isdigit() and int(n) <= 2 and len(nums) > 1)}
            if nums:
                number_sets.append((i, nums, text[:180]))
        if len(number_sets) < 2:
            return result
        seen: set[str] = set()
        drifted = []
        for i, s, ex in number_sets:
            new = s - seen
            if seen and new:
                drifted.append({
                    "turn": i,
                    "new_numbers": sorted(new),
                    "prior_numbers_seen": sorted(seen)[:12],
                    "excerpt": ex,
                })
            seen |= s
        if drifted:
            # New numbers can reflect added detail, not a conflict; keep confidence moderate and explainable.
            total_new = sum(len(d["new_numbers"]) for d in drifted)
            score = clamp01(0.32 + 0.08 * min(len(drifted), 4) + 0.03 * min(total_new, 6))
            result.observations.append(make_observation(
                label="numeric_detail_drift_observed",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "drift_events": drifted[:6],
                    "drift_event_count": len(drifted),
                    "note": "New numeric details appeared later; they may be added detail or a change—confirm counts, durations, or quantities.",
                },
                cue="Numeric details changed across responses; confirm counts, durations, or quantities.",
                turn_index=drifted[-1]["turn"],
            ))
        return result


class LocationReferenceDivergenceObserver:
    method_id = "cueliez.observations.consistency.location_divergence/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        locs: list[tuple[int, str, str]] = []
        for i, text in _subject_turns(transcript):
            for m in _LOCATION_RE.finditer(text):
                name = m.group(1).strip().rstrip(".,;:")
                if len(name) >= 3 and name.lower() not in {"the", "a", "an", "that", "this"}:
                    locs.append((i, name.lower(), text[:180]))
        if len(locs) < 2:
            return result
        uniq = {}
        for i, name, ex in locs:
            uniq.setdefault(name, []).append((i, ex))
        if len(uniq) >= 2:
            # Multiple locations may reflect movement across events; cue for clarification, not a conflict finding.
            score = clamp01(0.28 + 0.07 * min(len(uniq), 6))
            result.observations.append(make_observation(
                label="multiple_location_references_present",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "locations": list(uniq.keys())[:10],
                    "location_count": len(uniq),
                    "turns": {k: [t for t, _ in v][:3] for k, v in list(uniq.items())[:8]},
                    "note": "Multiple locations may describe different events or movement; confirm where each event occurred.",
                },
                cue="Multiple location references appear; confirm where each event occurred and reconcile the sequence.",
            ))
        return result


class SelfReferenceShiftObserver:
    method_id = "cueliez.observations.consistency.self_reference_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        turns = _subject_turns(transcript)
        if len(turns) < 3:
            return result
        counts = []
        for i, text in turns:
            words = re.findall(r"[A-Za-z']+", text.lower())
            if not words:
                continue
            first = len(re.findall(r"\b(i|me|my|mine|myself)\b", text.lower()))
            we = len(re.findall(r"\b(we|us|our|ours)\b", text.lower()))
            counts.append((i, first / max(1, len(words)), we / max(1, len(words))))
        if len(counts) < 3:
            return result
        first_vals = [c[1] for c in counts]
        avg = sum(first_vals) / len(first_vals)
        for i, fr, we in counts:
            if avg > 0.03 and fr < avg * 0.35 and we > fr:
                score = clamp01(0.35 + (avg - fr) * 4.0)
                result.observations.append(make_observation(
                    label="self_reference_pattern_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="consistency",
                    evidence={"first_person_rate": round(fr, 4), "we_rate": round(we, 4), "session_avg_first": round(avg, 4)},
                    cue="First-person reference pattern shifted; clarify personal actions versus group actions.",
                    turn_index=i,
                ))
                break
        return result
