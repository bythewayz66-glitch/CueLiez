"""Base types for CueLiez observation methods.

All observation methods must emit gate-compatible observations:
- confidence: {score: 0..1, model_id: non-empty}
- neutral labels (no verdict/deception language)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence


FORBIDDEN_LABELS = frozenset({
    "lying", "lie", "deception_confirmed", "guilty", "truthful",
    "deceptive", "dishonest", "honest",
})


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-") or "x"


def deterministic_cue_id(*, method: str, turn_index: Optional[int], label: str, category: str) -> str:
    """Deterministic cue id from (method, turn_index, label, category). Same inputs => same id."""
    ti = "na" if turn_index is None else str(int(turn_index))
    payload = f"{method}|{ti}|{label}|{category}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:12]
    return f"cue-t{ti}-{_slug(label)[:32]}-{digest}"


def normalize_priority(value: Any) -> str:
    v = str(value or "normal").strip().lower()
    return "high" if v == "high" else "normal"


def _validate_observation(
    label: str,
    confidence: Dict[str, Any],
    method: Any = None,
    category: Any = None,
    evidence: Any = None,
    priority: Any = None,
) -> tuple[str, float, str]:
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
    if method is not None and not str(method).strip():
        raise ValueError("method is required")
    if category is not None and not str(category).strip():
        raise ValueError("category is required")
    if evidence is not None and not isinstance(evidence, dict):
        raise ValueError("evidence must be a dict")
    if priority is not None and normalize_priority(priority) not in ("normal", "high"):
        raise ValueError("priority must be normal or high")
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
    cue_id: Optional[str] = None
    priority: str = "normal"

    def __post_init__(self) -> None:
        if self.evidence is None:
            self.evidence = {}
        self.priority = normalize_priority(self.priority)
        _validate_observation(self.label, self.confidence, self.method, self.category, self.evidence, self.priority)
        if not (str(self.cue_id).strip() if self.cue_id is not None else ""):
            self.cue_id = deterministic_cue_id(
                method=str(self.method), turn_index=self.turn_index, label=str(self.label), category=str(self.category)
            )

    def to_dict(self) -> Dict[str, Any]:
        _, score, model_id = _validate_observation(self.label, self.confidence, self.method, self.category, self.evidence, self.priority)
        conf = self.confidence or {}
        out: Dict[str, Any] = {
            "label": self.label,
            "confidence": {"score": score, "model_id": model_id},
            "category": self.category,
            "method": self.method,
            "evidence": dict(self.evidence or {}),
            "cue_id": str(self.cue_id),
            "priority": normalize_priority(self.priority),
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
    cue_id: Optional[str] = None,
    priority: str = "normal",
) -> Observation:
    return Observation(
        label=label,
        confidence={"score": clamp01(score), "model_id": method_id, "version": version},
        category=category,
        method=method_id,
        evidence=evidence or {},
        cue=cue,
        turn_index=turn_index,
        cue_id=cue_id,
        priority=priority,
    )


def text_of(turn: Any) -> str:
    if not isinstance(turn, Mapping):
        return ""
    for k in ("text", "utterance", "content", "transcript"):
        v = turn.get(k)
        if isinstance(v, str):
            return v
    return ""


def role_of(turn: Any) -> str:
    if not isinstance(turn, Mapping):
        return ""
    return str(turn.get("role") or turn.get("speaker") or "").lower()


def is_subject_turn(turn: Any) -> bool:
    if not isinstance(turn, Mapping):
        return False
    role = role_of(turn)
    if role in {"subject", "interviewee", "respondent", "suspect", "witness", "client", "patient"}:
        return True
    if role in {"officer", "interviewer", "agent", "clinician", "system"}:
        return False
    # Default: treat unknown roles as subject text for analysis unless explicitly marked.
    return turn.get("is_subject", True) is not False


SOURCE_TEXT_MAX = 500


def truncate_source(text: Any, max_len: int = SOURCE_TEXT_MAX) -> str:
    s = str(text or "")
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"


def source_span(turn: Any, turn_index: Optional[int] = None) -> Dict[str, Any]:
    """Quoted transcript evidence for a turn (neutral; not a finding)."""
    out: Dict[str, Any] = {}
    if turn_index is not None:
        out["turn_index"] = turn_index
    role = role_of(turn)
    if role:
        out["role"] = role
    out["source_text"] = truncate_source(text_of(turn))
    return out
