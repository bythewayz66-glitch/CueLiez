"""Testimony consistency observation methods.

Heuristic comparison across subject turns. These flag *possible conflicts* for
human review; they do not establish what occurred and are not verdicts.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from .base import (
    ObservationResult,
    clamp01,
    is_subject_turn,
    make_observation,
    role_of,
    source_span,
    text_of,
    truncate_source,
)
from .thresholds import (CLAIM_MIN_OVERLAP, CLAIM_MIN_SHARED_WORDS, CLAIM_TOPIC_DEDUP_OVERLAP,
                         TIMELINE_MIN_DISTINCT_CLOCK_TIMES, TIMELINE_MIN_DISTINCT_SPELLED_TIMES)

_NEG = re.compile(r"\b(no|not|never|didn't|did not|wasn't|was not|isn't|is not|don't|do not|can't|cannot)\b", re.I)
_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b|\b(midnight|noon|morning|afternoon|evening|night)\b", re.I)
_DATEISH_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|tomorrow|last\s+\w+|next\s+\w+)\b", re.I)
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_LOCATION_RE = re.compile(r"\b(?:at|in|to|from|near|inside|outside)\s+([A-Z][A-Za-z0-9'.-]*(?:\s+[A-Z][A-Za-z0-9'.-]*){0,3})")

_HOUR_WORD = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
)
_MINUTE_WORD = r"(?:o['’]?clock|thirty|fifteen|forty[- ]five|ten|twenty|five|oh\s+(?:one|two|three|four|five|six|seven|eight|nine))"
# Spelled-out time references common in transcripts (neutral review cue). Context/preposition
# reduces false positives on non-time uses like "eight people".
_SPELLED_TIME_RE = re.compile(
    rf"\b(?:(?:at|by|around|about|until|till|before|after|since|from|near)\s+)?({_HOUR_WORD})(?:[\s-]+{_MINUTE_WORD})\b"
    rf"|\b(?:at|by|around|about|until|till|before|after|since|from|near)\s+({_HOUR_WORD})\b",
    re.I,
)


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


def _key_overlap(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return inter / min(len(sa), len(sb))


class ClaimConflictObserver:
    method_id = "cueliez.observations.consistency.claim_conflict/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        items: list[tuple[int, str, int, str, Any]] = []
        for i, t in enumerate(transcript):
            if not is_subject_turn(t):
                continue
            text = text_of(t).strip()
            if len(text) < 12:
                continue
            key = _normalize_claim_key(text)
            key_words = key.split()
            if len(key_words) < 2:
                continue
            items.append((i, text, _polarity(text), key, t))

        candidates: list[tuple[float, tuple[int, int], int, int, Any, Any, int, int, str, float]] = []
        for idx, (i, text_i, pol_i, key_i, turn_i) in enumerate(items):
            for jdx in range(idx + 1, len(items)):
                j, text_j, pol_j, key_j, turn_j = items[jdx]
                if pol_i == pol_j:
                    continue
                overlap = _key_overlap(key_i, key_j)
                shared = len(set(key_i.split()) & set(key_j.split()))
                if shared < CLAIM_MIN_SHARED_WORDS or overlap < CLAIM_MIN_OVERLAP:
                    continue
                pair = (min(i, j), max(i, j))
                if pol_i == 1:
                    pos_i, pos_t, pos_turn = i, text_i, turn_i
                    neg_i, neg_t, neg_turn = j, text_j, turn_j
                else:
                    pos_i, pos_t, pos_turn = j, text_j, turn_j
                    neg_i, neg_t, neg_turn = i, text_i, turn_i
                topic = key_i if len(key_i.split()) >= len(key_j.split()) else key_j
                specificity = min(max(len(key_i.split()), len(key_j.split())), 8) / 8.0
                score = clamp01(0.46 + specificity * 0.16 + overlap * 0.12)
                candidates.append((score, pair, pos_i, neg_i, pos_turn, neg_turn, shared, max(i, j), topic, overlap))
        candidates.sort(key=lambda x: (-x[0], x[1][0], x[1][1]))
        emitted_pairs: set[tuple[int, int]] = set()
        emitted_topics: list[str] = []
        for score, pair, pos_i, neg_i, pos_turn, neg_turn, shared, ti, topic, overlap in candidates:
            if pair in emitted_pairs:
                continue
            # Reduce double-firing on same underlying issue: skip if very similar topic already reported.
            if any(_key_overlap(topic, et) >= CLAIM_TOPIC_DEDUP_OVERLAP for et in emitted_topics):
                continue
            emitted_pairs.add(pair)
            emitted_topics.append(topic)
            pos_span = source_span(pos_turn, pos_i)
            neg_span = source_span(neg_turn, neg_i)
            result.observations.append(make_observation(
                label="possible_statement_conflict",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "topic_key": topic,
                    "topic_key_overlap": round(overlap, 3),
                    "shared_key_words": shared,
                    "turn_indices": [pos_i, neg_i],
                    "turn_a": pos_i, "excerpt_a": truncate_source(pos_span.get("source_text", ""), 180), "polarity_a": "affirming", "role_a": pos_span.get("role", ""),
                    "turn_b": neg_i, "excerpt_b": truncate_source(neg_span.get("source_text", ""), 180), "polarity_b": "negating", "role_b": neg_span.get("role", ""),
                    "source_texts": [
                        {**pos_span, "polarity": "affirming"},
                        {**neg_span, "polarity": "negating"},
                    ],
                },
                cue="Statements on a similar topic differ in affirmation/negation; ask the subject to reconcile them.",
                turn_index=ti,
                priority="high",
            ))
        return result


def _norm_spelled_time(s: str) -> str:
    s = re.sub(r"\s+", " ", s.lower().strip())
    s = s.replace("o'clock", "oclock").replace("o’clock", "oclock")
    s = re.sub(r"^(?:at|by|around|about|until|till|before|after|since|from|near)\s+", "", s)
    return s


class TimelineInconsistencyObserver:
    method_id = "cueliez.observations.consistency.timeline_inconsistency/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        # (normalized_ref, turn_index, turn, raw_display)
        clock_refs: list[tuple[str, int, Any, str]] = []
        for i, t in enumerate(transcript):
            if not is_subject_turn(t):
                continue
            text = text_of(t).strip()
            if not text:
                continue
            # Digit clock times (existing behavior)
            for m in _TIME_RE.finditer(text):
                raw = m.group(0).lower()
                if re.search(r"\d", raw) and (":" in raw or re.search(r"\b(am|pm)\b", raw)):
                    clock_refs.append((re.sub(r"\s+", " ", raw).strip(), i, t, raw))
            # Spelled-out hour/minute references (e.g., "at eight", "eight-thirty")
            for m in _SPELLED_TIME_RE.finditer(text):
                raw = m.group(0).strip()
                norm = _norm_spelled_time(raw)
                if norm:
                    clock_refs.append((norm, i, t, raw.lower()))
        if len(clock_refs) < 2:
            return result
        uniq: dict[str, list[tuple[int, Any, str]]] = {}
        for norm, i, turn, raw in clock_refs:
            uniq.setdefault(norm, []).append((i, turn, raw))
        has_digit_ref = any(re.search(r"\d", raw) for _, _, _, raw in clock_refs)
        min_distinct = TIMELINE_MIN_DISTINCT_CLOCK_TIMES if has_digit_ref else TIMELINE_MIN_DISTINCT_SPELLED_TIMES
        if len(uniq) >= min_distinct:
            refs = list(uniq.keys())
            # A single event can legitimately involve multiple times (sequence); emit as a review cue, not inconsistency.
            score = clamp01(0.36 + 0.07 * min(len(refs), 6))
            source_texts = []
            seen_ti = set()
            for k, items in list(uniq.items())[:8]:
                for ti, turn, raw in items[:1]:
                    if ti in seen_ti:
                        continue
                    seen_ti.add(ti)
                    sp = source_span(turn, ti)
                    sp["time_ref"] = raw
                    source_texts.append(sp)
            result.observations.append(make_observation(
                label="multiple_time_references_present",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "distinct_time_refs": refs[:10],
                    "time_reference_count": len(refs),
                    "turn_indices": sorted(seen_ti),
                    "examples": {k: v[0][0] for k, v in list(uniq.items())[:6]},
                    "source_texts": source_texts[:8],
                    "note": "Multiple clock times may describe a sequence; verify ordering and consistency with the account.",
                },
                cue="Multiple specific time references appear across responses; verify the sequence and exact times.",
            ))
        return result


class DetailDriftObserver:
    method_id = "cueliez.observations.consistency.detail_drift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        number_sets: list[tuple[int, set[str], Any]] = []
        for i, t in enumerate(transcript):
            if not is_subject_turn(t):
                continue
            text = text_of(t).strip()
            if not text:
                continue
            nums = set(_NUMBER_RE.findall(text))
            # Drop trivial small ordinals/counters when other numbers are present to reduce noise.
            nums = {n for n in nums if not (n.isdigit() and int(n) <= 2 and len(nums) > 1)}
            if nums:
                number_sets.append((i, nums, t))
        if len(number_sets) < 2:
            return result
        seen: set[str] = set()
        drifted = []
        turn_map = {i: t for i, _, t in number_sets}
        for i, s, t in number_sets:
            new = s - seen
            if seen and new:
                drifted.append({
                    "turn": i,
                    "new_numbers": sorted(new),
                    "prior_numbers_seen": sorted(seen)[:12],
                    "source_text": truncate_source(text_of(t)),
                    "role": role_of(t),
                })
            seen |= s
        if drifted:
            # New numbers can reflect added detail, not a conflict; keep confidence moderate and explainable.
            total_new = sum(len(d["new_numbers"]) for d in drifted)
            score = clamp01(0.32 + 0.08 * min(len(drifted), 4) + 0.03 * min(total_new, 6))
            source_texts = [source_span(turn_map[d["turn"]], d["turn"]) for d in drifted[:6] if d["turn"] in turn_map]
            result.observations.append(make_observation(
                label="numeric_detail_drift_observed",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "drift_events": drifted[:6],
                    "drift_event_count": len(drifted),
                    "turn_indices": [d["turn"] for d in drifted[:6]],
                    "source_text": truncate_source(text_of(turn_map.get(drifted[-1]["turn"], {}))),
                    "source_texts": source_texts,
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
        locs: list[tuple[int, str, Any]] = []
        for i, t in enumerate(transcript):
            if not is_subject_turn(t):
                continue
            text = text_of(t).strip()
            if not text:
                continue
            for m in _LOCATION_RE.finditer(text):
                name = m.group(1).strip().rstrip(".,;:")
                if len(name) >= 3 and name.lower() not in {"the", "a", "an", "that", "this"}:
                    locs.append((i, name.lower(), t))
        if len(locs) < 2:
            return result
        uniq = {}
        for i, name, turn in locs:
            uniq.setdefault(name, []).append((i, turn))
        if len(uniq) >= 2:
            # Multiple locations may reflect movement across events; cue for clarification, not a conflict finding.
            score = clamp01(0.28 + 0.07 * min(len(uniq), 6))
            source_texts = []
            seen_ti = set()
            for name, items in list(uniq.items())[:8]:
                ti, turn = items[0]
                if ti not in seen_ti:
                    seen_ti.add(ti)
                    sp = source_span(turn, ti)
                    sp["location_ref"] = name
                    source_texts.append(sp)
            result.observations.append(make_observation(
                label="multiple_location_references_present",
                score=score,
                method_id=self.method_id,
                category="consistency",
                evidence={
                    "locations": list(uniq.keys())[:10],
                    "location_count": len(uniq),
                    "turn_indices": sorted(seen_ti),
                    "turns": {k: [t for t, _ in v][:3] for k, v in list(uniq.items())[:8]},
                    "source_texts": source_texts[:8],
                    "note": "Multiple locations may describe different events or movement; confirm where each event occurred.",
                },
                cue="Multiple location references appear; confirm where each event occurred and reconcile the sequence.",
            ))
        return result


class SelfReferenceShiftObserver:
    method_id = "cueliez.observations.consistency.self_reference_shift/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        turn_map = {i: t for i, t in enumerate(transcript) if is_subject_turn(t) and text_of(t).strip()}
        turns = [(i, text_of(t).strip()) for i, t in turn_map.items()]
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
                ev = {
                    "first_person_rate": round(fr, 4),
                    "we_rate": round(we, 4),
                    "session_avg_first_person_rate": round(avg, 4),
                    "turn_count": len(counts),
                }
                if i in turn_map:
                    ev.update(source_span(turn_map[i], i))
                result.observations.append(make_observation(
                    label="self_reference_pattern_shift_observed",
                    score=score,
                    method_id=self.method_id,
                    category="consistency",
                    evidence=ev,
                    cue="First-person reference pattern shifted; clarify personal actions versus group actions.",
                    turn_index=i,
                ))
                break
        return result
