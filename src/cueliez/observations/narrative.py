"""Narrative-structure and accountability observation methods.

Literature-aligned cues (PEACE / cognitive interviewing / statement analysis
research traditions) without deception claims. Probabilistic indicators for
human review only.
"""

from __future__ import annotations

import re
from typing import Any, List, Mapping, Sequence

from .base import ObservationResult, clamp01, is_subject_turn, make_observation, source_span, text_of

_WORD_RE = re.compile(r"[A-Za-z']+")
_TIME_MARKERS = re.compile(
    r"\b(?:then|after(?:ward)?|before|later|earlier|next|previously|"
    r"meanwhile|subsequently|first|second|finally|eventually|"
    r"at\s+\d|o'clock|am|pm|morning|afternoon|evening|night)\b",
    re.I,
)
_SENSORY = re.compile(
    r"\b(?:saw|heard|smelled|felt|touched|noticed|looked|sounded|"
    r"remember\s+seeing|remember\s+hearing|could\s+see|could\s+hear)\b",
    re.I,
)
_AGENCY_SELF = re.compile(
    r"\b(?:i\s+(?:did|went|said|called|drove|took|left|arrived|decided|chose|told))\b",
    re.I,
)
_EXTERNALIZED = re.compile(
    r"\b(?:it\s+just\s+happened|things\s+happened|one\s+thing\s+led|"
    r"got\s+(?:out\s+of\s+hand|carried\s+away)|was\s+made\s+to|"
    r"had\s+to\s+because|they\s+made\s+me|circumstances)\b",
    re.I,
)
_SPECIFIC_DETAIL = re.compile(
    r"\b(?:\d{1,2}:\d{2}|\d+\s*(?:minutes?|hours?|blocks?|miles?)|"
    r"red|blue|black|white|green|left|right|north|south|"
    r"license|plate|badge|shirt|jacket)\b",
    re.I,
)


def _subject_turns(turns: Sequence[Mapping[str, Any]]) -> List[tuple[int, str]]:
    out = []
    for i, t in enumerate(turns or []):
        if not isinstance(t, Mapping):
            continue
        if is_subject_turn(t):
            txt = text_of(t)
            if txt.strip():
                out.append((i, txt))
    return out


class TemporalStructureObserver:
    """Sparse temporal scaffolding in extended free-recall accounts."""

    method = "narrative.temporal_structure"
    category = "narrative"
    model_id = "narrative-temporal-v1"

    def observe(self, turns: Sequence[Mapping[str, Any]]) -> ObservationResult:
        subjects = _subject_turns(turns)
        if len(subjects) < 2:
            return ObservationResult(method=self.method, observations=[])
        total_words = 0
        total_markers = 0
        spans = []
        for idx, txt in subjects:
            words = _WORD_RE.findall(txt)
            total_words += len(words)
            markers = _TIME_MARKERS.findall(txt)
            total_markers += len(markers)
            if markers:
                spans.append(source_span(idx, txt[:120]))
        if total_words < 40:
            return ObservationResult(method=self.method, observations=[])
        density = total_markers / max(total_words / 20.0, 1.0)
        if density >= 0.8 or total_markers >= 4:
            return ObservationResult(method=self.method, observations=[])
        score = clamp01(0.35 + (0.45 * (1.0 - min(density, 1.0))) + min(total_words / 200.0, 0.15))
        if score < 0.40:
            return ObservationResult(method=self.method, observations=[])
        obs = make_observation(
            label="sparse_temporal_structure",
            score=score,
            method_id=self.method,
            category=self.category,
            evidence={
                "subject_words": total_words,
                "temporal_markers": total_markers,
                "density_per_20w": round(density, 3),
                "spans": spans[:3],
            },
            cue="Subject account has relatively few temporal sequence markers for its length. Consider a neutral prompt about order of events.",
            turn_index=subjects[-1][0],
        )
        return ObservationResult(method=self.method, observations=[obs] if obs else [])


class SensoryDetailObserver:
    """Low sensory-detail density in extended accounts."""

    method = "narrative.sensory_detail"
    category = "narrative"
    model_id = "narrative-sensory-v1"

    def observe(self, turns: Sequence[Mapping[str, Any]]) -> ObservationResult:
        subjects = _subject_turns(turns)
        if len(subjects) < 2:
            return ObservationResult(method=self.method, observations=[])
        total_words = sum(len(_WORD_RE.findall(t)) for _, t in subjects)
        if total_words < 50:
            return ObservationResult(method=self.method, observations=[])
        hits = sum(len(_SENSORY.findall(t)) for _, t in subjects)
        ratio = hits / max(total_words / 30.0, 1.0)
        if ratio >= 0.6 or hits >= 3:
            return ObservationResult(method=self.method, observations=[])
        score = clamp01(0.34 + 0.4 * (1.0 - min(ratio, 1.0)) + min(total_words / 250.0, 0.12))
        if score < 0.40:
            return ObservationResult(method=self.method, observations=[])
        obs = make_observation(
            label="low_sensory_detail_density",
            score=score,
            method_id=self.method,
            category=self.category,
            evidence={"subject_words": total_words, "sensory_hits": hits, "ratio": round(ratio, 3)},
            cue="Extended account contains few sensory-detail markers. A cognitive-interview style prompt about what was seen or heard may help.",
            turn_index=subjects[-1][0],
        )
        return ObservationResult(method=self.method, observations=[obs] if obs else [])


class AgencyFramingObserver:
    """Elevated externalized framing relative to self-agency markers."""

    method = "narrative.agency_framing"
    category = "narrative"
    model_id = "narrative-agency-v1"

    def observe(self, turns: Sequence[Mapping[str, Any]]) -> ObservationResult:
        subjects = _subject_turns(turns)
        if not subjects:
            return ObservationResult(method=self.method, observations=[])
        self_hits = 0
        ext_hits = 0
        last_idx = subjects[-1][0]
        examples = []
        for idx, txt in subjects:
            s = _AGENCY_SELF.findall(txt)
            e = _EXTERNALIZED.findall(txt)
            self_hits += len(s)
            ext_hits += len(e)
            if e:
                examples.append(source_span(idx, e[0] if e else txt[:80]))
        total = self_hits + ext_hits
        if total < 2 or ext_hits == 0:
            return ObservationResult(method=self.method, observations=[])
        ext_ratio = ext_hits / total
        if ext_ratio < 0.45:
            return ObservationResult(method=self.method, observations=[])
        score = clamp01(0.38 + 0.35 * ext_ratio + min(ext_hits / 8.0, 0.15))
        obs = make_observation(
            label="elevated_externalized_framing",
            score=score,
            method_id=self.method,
            category=self.category,
            evidence={
                "self_agency_hits": self_hits,
                "externalized_hits": ext_hits,
                "externalized_ratio": round(ext_ratio, 3),
                "examples": examples[:3],
            },
            cue="Account shows relatively elevated externalized framing vs. self-agency markers. Consider neutral clarification of the subject's described role.",
            turn_index=last_idx,
            priority="normal",
        )
        return ObservationResult(method=self.method, observations=[obs] if obs else [])


class SpecificityShiftObserver:
    """Specificity drop between freer recall and prompted answers."""

    method = "narrative.specificity_shift"
    category = "narrative"
    model_id = "narrative-specificity-v1"

    def observe(self, turns: Sequence[Mapping[str, Any]]) -> ObservationResult:
        free_words, free_specs = 0, 0
        prompt_words, prompt_specs = 0, 0
        last_prompt_idx = None
        prev_role = None
        for i, t in enumerate(turns or []):
            if not isinstance(t, Mapping):
                continue
            txt = text_of(t)
            words = _WORD_RE.findall(txt)
            specs = len(_SPECIFIC_DETAIL.findall(txt))
            if is_subject_turn(t):
                if prev_role in ("interviewer", "officer", "detective", "therapist", "clinician"):
                    prompt_words += len(words)
                    prompt_specs += specs
                    last_prompt_idx = i
                else:
                    free_words += len(words)
                    free_specs += specs
            role = str(t.get("role") or t.get("speaker") or "").strip().lower()
            prev_role = role
        if free_words < 25 or prompt_words < 15:
            return ObservationResult(method=self.method, observations=[])
        free_rate = free_specs / max(free_words / 20.0, 1.0)
        prompt_rate = prompt_specs / max(prompt_words / 20.0, 1.0)
        if free_rate <= 0 or prompt_rate >= free_rate * 0.7:
            return ObservationResult(method=self.method, observations=[])
        drop = (free_rate - prompt_rate) / free_rate
        score = clamp01(0.40 + 0.4 * drop)
        if score < 0.45:
            return ObservationResult(method=self.method, observations=[])
        obs = make_observation(
            label="specificity_drop_under_prompting",
            score=score,
            method_id=self.method,
            category=self.category,
            evidence={
                "free_recall_words": free_words,
                "prompted_words": prompt_words,
                "free_specificity_rate": round(free_rate, 3),
                "prompted_specificity_rate": round(prompt_rate, 3),
                "relative_drop": round(drop, 3),
            },
            cue="Specific detail density appears lower in prompted answers than in freer recall. Consider inviting another free-recall pass or concrete examples.",
            turn_index=last_prompt_idx,
        )
        return ObservationResult(method=self.method, observations=[obs] if obs else [])
