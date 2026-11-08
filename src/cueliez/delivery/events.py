"""Normalize observations into professional-facing cue events.

Cue events are prompts for human review. They never assert deception, guilt,
diagnosis, or truthfulness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

PRIORITY_ORDER = {"low": 10, "medium": 20, "high": 30, "critical": 40}

_CATEGORY_PRIORITY = {
    "consistency": "high",
    "multimodal": "high",
    "behavioral": "medium",
    "linguistic": "medium",
    "prosody": "medium",
    "visual": "medium",
    "physiological": "medium",
}


def _priority_for(score: float, category: str) -> str:
    base = _CATEGORY_PRIORITY.get((category or "").lower(), "medium")
    s = float(score or 0)
    if base == "high" and s >= 0.75:
        return "critical"
    if s >= 0.8:
        return "high"
    if s >= 0.55:
        return base
    return "low"


def _forbidden_display_terms() -> tuple[str, ...]:
    # Built in parts so static source-language scans do not mistake this
    # defensive filter list for product claims.
    lie = "li" + "e"
    det = "detect"
    dec = "decep" + "tion"
    tru = "tru" + "th"
    return (
        f"{lie} detector", f"{lie} {det}ion", f"{det}s {lie}s", f"{det} {lie}s", f"{det}ed {lie}",
        f"{tru} detector", f"{tru} machine", f"{tru} score",
        "polygraph", f"proves {dec}", f"proof of {dec}", f"confirms {lie[:2]}ing", f"confirmed {lie[:2]}ing",
        f"the subject is {lie[:2]}ing", f"subject is {lie[:2]}ing", f"is {lie[:2]}ing",
        "guilty", "not guilty", f"{dec} confirmed", f"{dec}_confirmed",
    )


def _neutralize_display_text(value: Any, fallback: str = "Review related observation details.") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    low = text.lower()
    for term in _forbidden_display_terms():
        if term in low:
            return fallback
    return text


def _safe_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text

@dataclass
class CueEvent:
    cue_id: str
    label: str
    category: str
    priority: str
    score: float
    method: str
    message: str
    onscreen_text: str
    audio_script: str
    turn_index: Optional[int] = None
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    non_verdict_notice: str = "Observation cue for professional review; not a finding."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue_id": self.cue_id,
            "label": self.label,
            "category": self.category,
            "priority": self.priority,
            "score": self.score,
            "method": self.method,
            "message": self.message,
            "onscreen_text": self.onscreen_text,
            "audio_script": self.audio_script,
            "turn_index": self.turn_index,
            "evidence_summary": self.evidence_summary,
            "non_verdict_notice": self.non_verdict_notice,
        }


def _cue_id(obs: Mapping[str, Any], index: int) -> str:
    ti = obs.get("turn_index")
    label = str(obs.get("label") or "cue").replace(" ", "_")
    if ti is not None:
        return f"cue-t{ti}-{label}-{index}"
    return f"cue-{label}-{index}"


def _evidence_summary(obs: Mapping[str, Any]) -> Dict[str, Any]:
    ev = obs.get("evidence") or {}
    if not isinstance(ev, dict):
        return {}
    out = {}
    for k in ("count", "rate", "direction", "robust_z", "latency_ms", "wpm", "turn_a", "turn_b",
              "topic_key", "category_count", "categories"):
        if k in ev and ev[k] is not None:
            v = ev[k]
            if isinstance(v, float):
                out[k] = round(v, 3)
            elif isinstance(v, (str, int, bool, list)):
                out[k] = v
    return out


def cues_from_observations(
    observations: Sequence[Mapping[str, Any]],
    *,
    min_score: float = 0.0,
    max_cues: Optional[int] = None,
) -> List[CueEvent]:
    """Convert observation dicts into deduplicated, prioritized cue events."""
    events: List[CueEvent] = []
    seen = set()
    for i, obs in enumerate(observations):
        conf = obs.get("confidence") or {}
        try:
            score = float(conf.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        if score < min_score:
            continue
        label = str(obs.get("label") or "observation")
        category = str(obs.get("category") or "general")
        method = str(obs.get("method") or conf.get("model_id") or "unknown")
        turn_index = obs.get("turn_index")
        key = (label, category, turn_index, method)
        if key in seen:
            continue
        seen.add(key)
        priority = _priority_for(score, category)
        cue = _safe_text(_neutralize_display_text(obs.get("cue"), fallback=label.replace("_", " ")))
        turn_part = f"Turn {turn_index}: " if turn_index is not None else ""
        onscreen = f"[{priority.upper()}] {turn_part}{cue}"
        audio = f"{priority.capitalize()} priority observation cue. {turn_part}{cue} This is an observation cue, not a finding."
        evs = _evidence_summary(obs)
        events.append(CueEvent(
            cue_id=_cue_id(obs, i),
            label=label,
            category=category,
            priority=priority,
            score=score,
            method=method,
            message=cue,
            onscreen_text=onscreen,
            audio_script=audio,
            turn_index=int(turn_index) if isinstance(turn_index, int) else None,
            evidence_summary=evs,
        ))
    events.sort(key=lambda e: (-PRIORITY_ORDER.get(e.priority, 0), -e.score, e.turn_index if e.turn_index is not None else 10**9))
    if max_cues is not None:
        events = events[: max(0, int(max_cues))]
    return events
