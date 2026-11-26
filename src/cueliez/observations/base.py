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


def calibrate_score(value: Any, *, method_id: str | None = None) -> float:
    """Normalize heuristic observer score to [0,1] (consistent; versionable hook).

    Current behavior: clamp normalization for stability (identity within bounds).
    Must not be interpreted as probability of deception, credibility, guilt, or any finding.
    """
    _ = method_id
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return clamp01(v)


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
        confidence={"score": calibrate_score(score, method_id=method_id), "model_id": method_id, "version": version},
        category=category,
        method=method_id,
        evidence=evidence or {},
        cue=cue,
        turn_index=turn_index,
        cue_id=cue_id,
        priority=priority,
    )


def feature_value(turn: Any, *keys: str) -> float | None:
    """Read a numeric derived-feature value from a turn.

    Feature metadata may arrive flat on the turn, inside a ``features`` dict,
    or nested one level deeper (``turn["features"]["audio_features"]``,
    ``turn["features"]["camera"]``, ``turn["features"]["wearable"]``), or in
    a top-level ``audio_features`` / ``camera`` / ``wearable`` dict on the
    turn. Only caller-supplied derived numeric features are read here; no
    raw audio/video is processed and no feature is invented when absent
    (returns ``None``).
    """
    if not isinstance(turn, Mapping):
        return None
    for k in keys:
        v = turn.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    containers: list[Any] = []
    for name in ("features", "audio_features", "camera", "wearable", "prosody",
                 "acoustic", "visual", "video_features", "vision", "physio",
                 "physiological", "biometric_features", "meta", "metadata"):
        c = turn.get(name)
        if isinstance(c, Mapping):
            containers.append(c)
            # One level of nesting: features.audio_features / .camera / .wearable
            for sub in ("audio_features", "camera", "wearable", "prosody", "visual", "physiological"):
                s = c.get(sub)
                if isinstance(s, Mapping):
                    containers.append(s)
    for c in containers:
        for k in keys:
            v = c.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def feature_dict(turn: Any, *names: str) -> dict[str, Any]:
    """Return a merged dict of caller-supplied derived features for a turn.

    Merges ``turn["features"]`` (including its ``audio_features`` / ``camera`` /
    ``wearable`` sub-dicts) and any top-level container named in ``names``.
    Returns ``{}`` when no derived features were supplied. Values are passed
    through unchanged; callers must treat them as supplied data only.
    """
    out: dict[str, Any] = {}
    if not isinstance(turn, Mapping):
        return out
    for name in ("features", *names):
        c = turn.get(name)
        if isinstance(c, Mapping):
            for k, v in c.items():
                if isinstance(v, Mapping):
                    out.setdefault(k, {})
                    if isinstance(out[k], dict):
                        out[k].update(v)
                else:
                    out[k] = v
    return out


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
