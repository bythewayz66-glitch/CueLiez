"""Base types for CueLiez observation methods.

All observation methods must emit gate-compatible observations:
- confidence: {score: 0..1, model_id: non-empty}
- neutral labels (no verdict/deception language)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence


FORBIDDEN_LABELS = frozenset({
    "lying", "lie", "deception_confirmed", "guilty", "truthful",
    "deceptive", "dishonest", "honest",
})


def _validate_observation(label: str, confidence: Dict[str, Any]) -> tuple[str, float, str]:
    lab = (label or "").strip().lower()
    if lab in FORBIDDEN_LABELS:
        raise ValueError(f"Forbidden verdict label: {label!r}")
    conf = confidence or {}
    score = conf.get("score")
    if not isinstance(score, (int, float)) or score < 0.0 or score > 1.0:
        raise ValueError(f"confidence.score must be in [0,1], got {score!r}")
    model_id = conf.get("model_id")
    if not (str(model_id).strip() if model_id is not None else ""):
        raise ValueError("confidence.model_id is required")
    return lab, float(score), str(model_id)


@dataclass
class Observation:
    """A single gate-compatible observation."""

    label: str
    confidence: Dict[str, Any]
    category: str
    method: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    cue: Optional[str] = None
    turn_index: Optional[int] = None

    def __post_init__(self) -> None:
        _validate_observation(self.label, self.confidence)

    def to_dict(self) -> Dict[str, Any]:
        _, score, model_id = _validate_observation(self.label, self.confidence)
        conf = self.confidence or {}
        out: Dict[str, Any] = {
            "label": self.label,
            "confidence": {"score": score, "model_id": model_id},
            "category": self.category,
            "method": self.method,
            "evidence": self.evidence,
        }
        if "version" in conf:
            out["confidence"]["version"] = conf["version"]
        if self.cue:
            out["cue"] = self.cue
        if self.turn_index is not None:
            out["turn_index"] = self.turn_index
        return out


@dataclass
class ObservationResult:
    method: str
    observations: List[Observation] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [o.to_dict() for o in self.observations]


class Observer(Protocol):
    method_id: str

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        ...


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def make_observation(
    *,
    label: str,
    score: float,
    method_id: str,
    category: str,
    evidence: Optional[Dict[str, Any]] = None,
    cue: Optional[str] = None,
    turn_index: Optional[int] = None,
    version: str = "v1",
) -> Observation:
    return Observation(
        label=label,
        confidence={"score": clamp01(score), "model_id": method_id, "version": version},
        category=category,
        method=method_id,
        evidence=evidence or {},
        cue=cue,
        turn_index=turn_index,
    )


def text_of(turn: Mapping[str, Any]) -> str:
    for k in ("text", "utterance", "content", "transcript"):
        v = turn.get(k)
        if isinstance(v, str):
            return v
    return ""


def role_of(turn: Mapping[str, Any]) -> str:
    return str(turn.get("role") or turn.get("speaker") or "").lower()


def is_subject_turn(turn: Mapping[str, Any]) -> bool:
    role = role_of(turn)
    if role in {"subject", "interviewee", "respondent", "suspect", "witness", "client", "patient"}:
        return True
    if role in {"officer", "interviewer", "agent", "clinician", "system"}:
        return False
    # Default: treat unknown roles as subject text for analysis unless explicitly marked.
    return turn.get("is_subject", True) is not False
