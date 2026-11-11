"""Stable transcript ingest contract (Phase 7). Observation/cue workflow input only.

Loads transcript JSON from supported sources and can attach neutral source-artifact
metadata (original artifact reference) to an observation package before seal.
No findings/verdicts. Sealed packages remain the attachable artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from .observations.runner import ObservationRunner, default_runner

WRAPPER_KEYS = ("turns", "transcript", "messages", "utterances", "segments", "items",
                "entries", "results", "dialogue", "conversation")
ROLE_KEYS = ("role", "speaker", "speaker_role", "speakerRole", "speaker_type", "speakerType",
             "participant", "participant_role", "participantRole", "channel", "label", "actor")
TEXT_KEYS = ("text", "utterance", "content", "transcript", "body", "message", "value")
TOKEN_KEYS = ("words", "tokens")
TIMING_KEYS = (
    "start", "end", "start_time", "end_time", "startTime", "endTime", "start_ms", "end_ms",
    "timestamp", "time", "offset", "offset_ms", "duration", "duration_ms", "duration_s",
    "speech_duration_ms", "speech_duration_s", "response_latency_ms", "latency_ms", "delay_ms",
    "response_latency_s", "latency_s", "pause_total_ms", "pause_duration_ms", "silence_ms", "pause_count",
)
FEATURE_KEYS = (
    "prosody", "acoustic", "audio_features", "features", "gaze_aversion_ratio", "blink_rate",
    "heart_rate_bpm", "hrv_ms", "hrv_rmssd_ms",
)
NON_TEXT_CONTENT_KEYS = TIMING_KEYS + FEATURE_KEYS

EMPTY_TEXT_POLICY = "flag"
EMPTY_TEXT_POLICIES = ("flag", "reject")
EMPTY_TEXT_FLAG = "empty_text"
INGEST_FLAGS_KEY = "ingest_flags"
UNMAPPED_KEY = "ingest_unmapped"

INGEST_ERROR_CODES = (
    "ingest_invalid_input",
    "ingest_invalid_turn",
    "ingest_ambiguous_turn",
    "ingest_unattributed_turn",
    "ingest_empty_turn",
    "ingest_unrecognised_structure",
    "ingest_ambiguous_structure",
    "ingest_empty_transcript",
)

_SUBJECT_ROLES = {
    "subject", "interviewee", "respondent", "suspect", "witness", "client", "patient",
    "caller", "callee", "deponent", "speaker_a", "person_a", "defendant",
}
_INTERVIEWER_ROLES = {
    "interviewer", "officer", "agent", "clinician", "system", "operator", "investigator",
    "detective", "counselor", "therapist", "speaker_b", "person_b", "questioner",
}
_CANONICAL_ROLES = ("subject", "interviewer")


class IngestError(ValueError):
    """Ingest failure with a stable code; subclasses ValueError."""

    def __init__(self, code: str, message: str, *, turn_index: Optional[int] = None):
        self.code = code
        self.message = message
        self.turn_index = turn_index
        super().__init__(f"[{code}] {message}")

    def as_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"ok": False, "error_code": self.code, "error": self.message}
        if self.turn_index is not None:
            out["turn_index"] = self.turn_index
        return out


def _slug(label: Any) -> str:
    return str(label).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_role(role: str) -> str:
    if not role:
        return ""
    r = _slug(role)
    if r in _SUBJECT_ROLES:
        return "subject"
    if r in _INTERVIEWER_ROLES:
        return "interviewer"
    # token matching for labels such as "Officer A"
    parts = set(r.split("_"))
    if parts & {"officer", "interviewer", "detective", "agent", "investigator", "operator", "clinician", "therapist", "counselor"}:
        return "interviewer"
    if parts & {"subject", "suspect", "witness", "respondent", "interviewee", "defendant", "deponent", "patient", "client"}:
        return "subject"
    return r


def _where(index: Optional[int]) -> str:
    return "turn" if index is None else f"turn[{index}]"


def _text_from_value(key: str, value: Any, index: Optional[int]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for x in value:
            if isinstance(x, str):
                parts.append(x)
            elif isinstance(x, Mapping):
                w = x.get("text") or x.get("word") or x.get("token") or x.get("punctuated_word") or ""
                parts.append(str(w))
            else:
                raise IngestError("ingest_invalid_turn", f"{_where(index)} field {key!r} holds a {type(x).__name__} item; expected strings or objects", turn_index=index)
        return " ".join(p.strip() for p in parts if str(p).strip())
    raise IngestError("ingest_invalid_turn", f"{_where(index)} field {key!r} must be a string or a list of words, got {type(value).__name__}", turn_index=index)


def canonicalize_turn(turn: Any, *, index: Optional[int] = None) -> Dict[str, Any]:
    """Map a vendor-like turn to canonical {role, text, ...}; every input key is kept.

    Raises IngestError for a turn that is not a mapping or string, for conflicting
    role or text fields, and for text fields of an unusable type. An unmappable or
    missing role is returned as-is; validate_transcript_turns rejects it.
    """
    if isinstance(turn, str):
        return {"role": "subject", "text": turn}
    if not isinstance(turn, Mapping):
        raise IngestError("ingest_invalid_turn", f"{_where(index)} must be an object or a string, got {type(turn).__name__}", turn_index=index)

    role_cands = [(k, str(turn[k]).strip()) for k in ROLE_KEYS if turn.get(k) is not None and str(turn[k]).strip()]
    mapped = [(k, v, _normalize_role(v)) for k, v in role_cands]
    mapped_ok = [m for m in mapped if m[2] in _CANONICAL_ROLES]
    if len({m[2] for m in mapped_ok}) > 1:
        raise IngestError("ingest_ambiguous_turn", f"{_where(index)} carries conflicting speaker fields: " + ", ".join(f"{k}={v!r}" for k, v, _ in mapped_ok), turn_index=index)
    if mapped_ok:
        role_key, role_label, role = mapped_ok[0]
    elif mapped:
        role_key, role_label, role = mapped[0]
    else:
        role_key, role_label, role = None, "", ""

    text_cands: List[tuple] = []
    for k in TEXT_KEYS:
        t = _text_from_value(k, turn.get(k), index)
        if t.strip():
            text_cands.append((k, t))
    if len({t for _, t in text_cands}) > 1:
        raise IngestError("ingest_ambiguous_turn", f"{_where(index)} carries conflicting text fields: " + ", ".join(k for k, _ in text_cands), turn_index=index)
    if text_cands:
        text_key, text = text_cands[0]
    else:
        text_key, text = None, ""
        for k in TOKEN_KEYS:
            t = _text_from_value(k, turn.get(k), index)
            if t.strip():
                text = t
                break

    consumed = {role_key, text_key}
    out: Dict[str, Any] = {}
    unmapped: Dict[str, Any] = {}
    for k, v in turn.items():
        if k in consumed:
            continue
        if k in ("role", "text"):
            if v is not None and str(v).strip():
                unmapped[k] = v
            continue
        out[k] = v
    out["role"] = role
    out["text"] = text
    if role_label and role in _CANONICAL_ROLES and _slug(role_label) != role:
        out["speaker_original"] = role_label
    if unmapped:
        out[UNMAPPED_KEY] = unmapped
    return out


def _check_policy(policy: Optional[str]) -> str:
    p = EMPTY_TEXT_POLICY if policy is None else policy
    if p not in EMPTY_TEXT_POLICIES:
        raise ValueError(f"empty_text_policy must be one of {EMPTY_TEXT_POLICIES}, got {p!r}")
    return p


def _extract_turns(raw: Any) -> tuple:
    """Return (turns, container_key, ignored_wrapper_keys) or raise IngestError."""
    if isinstance(raw, Mapping):
        present = [k for k in WRAPPER_KEYS if k in raw]
        if not present:
            raise IngestError("ingest_unrecognised_structure", f"object has no recognised turn container (expected one of {', '.join(WRAPPER_KEYS)}); found keys: {sorted(map(str, raw))}")
        if len(present) > 1:
            raise IngestError("ingest_ambiguous_structure", f"object has more than one turn container: {', '.join(present)}")
        key = present[0]
        container = raw[key]
        if isinstance(container, (str, bytes)) or not isinstance(container, Sequence):
            raise IngestError("ingest_unrecognised_structure", f"turn container {key!r} must be a list of turns, got {type(container).__name__}")
        return container, key, sorted(str(k) for k in raw if k != key)
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise IngestError("ingest_unrecognised_structure", f"transcript must be a list of turns or a wrapper object, got {type(raw).__name__}")
    return raw, None, []


def _validate(turns: Sequence[Any], policy: str) -> tuple:
    out: List[Dict[str, Any]] = []
    flagged: List[Dict[str, Any]] = []
    for i, t in enumerate(turns):
        ct = canonicalize_turn(t, index=i)
        if ct["role"] not in _CANONICAL_ROLES:
            label = ct["role"] or None
            detail = f"original label {label!r}" if label else "no speaker field"
            raise IngestError("ingest_unattributed_turn", f"turn[{i}] cannot be attributed to subject or interviewer ({detail})", turn_index=i)
        if not ct["text"].strip():
            if policy == "reject" and not any(k in ct for k in NON_TEXT_CONTENT_KEYS):
                raise IngestError("ingest_empty_turn", f"turn[{i}] has no text and no timing or feature content", turn_index=i)
            ct[INGEST_FLAGS_KEY] = [*ct.get(INGEST_FLAGS_KEY, []), EMPTY_TEXT_FLAG]
            flagged.append({"index": i, "code": EMPTY_TEXT_FLAG})
        out.append(ct)
    if not out:
        raise IngestError("ingest_empty_transcript", "transcript has no turns")
    if len(flagged) == len(out):
        raise IngestError("ingest_empty_transcript", f"all {len(out)} turns have empty text")
    return out, flagged


def validate_transcript_turns(turns: Any, *, empty_text_policy: Optional[str] = None) -> List[Dict[str, Any]]:
    """Canonicalize and validate turns; raises IngestError (a ValueError) on any unusable input."""
    policy = _check_policy(empty_text_policy)
    seq, _, _ = _extract_turns(turns)
    out, _ = _validate(seq, policy)
    return out


def _read_source(source: Any) -> tuple:
    """Return (raw_json_value, source_name)."""
    name: Optional[str] = None
    try:
        if isinstance(source, Path) or (isinstance(source, str) and not source.lstrip().startswith(("{", "["))):
            p = Path(source)
            name = str(p)
            return json.loads(p.read_text(encoding="utf-8")), name
        if isinstance(source, str):
            return json.loads(source), None
        if hasattr(source, "read"):
            name = getattr(source, "name", None)
            return json.load(source), name if isinstance(name, str) else None
    except json.JSONDecodeError as e:
        raise IngestError("ingest_invalid_input", f"input is not valid JSON: {e}") from e
    except (OSError, UnicodeDecodeError) as e:
        raise IngestError("ingest_invalid_input", f"input could not be read: {e}") from e
    return source, None


def _ingest(source: Any, empty_text_policy: Optional[str]) -> tuple:
    policy = _check_policy(empty_text_policy)
    raw, name = _read_source(source)
    seq, container, ignored = _extract_turns(raw)
    turns, flagged = _validate(seq, policy)
    report = {
        "input_turn_count": len(seq),
        "accepted_turn_count": len(turns),
        "container": container or "root",
        "ignored_wrapper_keys": ignored,
        "flagged_turns": flagged,
        "empty_text_policy": policy,
    }
    return turns, report, name


def normalize_transcript_with_report(source: Any, *, empty_text_policy: Optional[str] = None) -> tuple:
    """Return (turns, ingest_report). Raises IngestError; never returns a partial or empty transcript."""
    turns, report, _ = _ingest(source, empty_text_policy)
    return turns, report


def normalize_transcript(source: Any, *, empty_text_policy: Optional[str] = None) -> List[Dict[str, Any]]:
    """Normalize vendor/common transcript JSON shapes to canonical turns [{role,text,...}]."""
    return normalize_transcript_with_report(source, empty_text_policy=empty_text_policy)[0]


def load_transcript(source: Union[str, Path, Mapping[str, Any], Sequence[Any], Any], *, empty_text_policy: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load and normalize a transcript from a path, JSON string, file-like object, list or wrapper dict."""
    return normalize_transcript(source, empty_text_policy=empty_text_policy)


def transcript_source_hash(transcript: Any) -> str:
    """SHA-256 of canonical JSON representation (neutral integrity reference)."""
    payload = json.dumps(transcript, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_ingested_package(
    source: Union[str, Path, Mapping[str, Any], Sequence[Any], Any],
    *,
    runner: Optional[ObservationRunner] = None,
    session_id: Optional[str] = None,
    annotations: Optional[Dict[str, Any]] = None,
    include_source_artifact: bool = True,
) -> Dict[str, Any]:
    """Build an observation package from transcript JSON (stable ingest path).

    Attaches neutral `source_artifact` metadata when include_source_artifact is True
    (reference only; no findings). Package may be sealed via gate-hardened seal path.
    """
    transcript, report, source_name = _ingest(source, None)
    r = runner or default_runner()
    pkg = r.build_package(transcript, session_id=session_id, annotations=annotations)
    if include_source_artifact:
        pkg["source_artifact"] = {
            "type": "transcript_json",
            "name": source_name,
            "transcript_sha256": transcript_source_hash(transcript),
            "turn_count": len(transcript),
            "ingest_report": report,
        }
    return pkg
