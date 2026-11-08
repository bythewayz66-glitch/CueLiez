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

from .observations.runner import ObservationRunner, _normalize_transcript, default_runner

_ROLE_KEYS = ("role", "speaker", "speaker_role", "speakerRole", "speaker_type", "speakerType",
              "participant", "participant_role", "participantRole", "channel", "label", "actor")
_TEXT_KEYS = ("text", "utterance", "content", "transcript", "body", "message", "value")
# Common timestamp/metadata keys preserved when present
_META_KEYS = (
    "start", "end", "start_time", "end_time", "startTime", "endTime", "start_ms", "end_ms",
    "timestamp", "time", "offset", "offset_ms", "duration", "duration_ms",
    "speaker_id", "speakerId", "participant_id", "participantId", "turn_id", "id",
    "confidence", "asr_confidence", "language", "source",
)

_SUBJECT_ROLES = {
    "subject", "interviewee", "respondent", "suspect", "witness", "client", "patient",
    "caller", "callee", "deponent", "speaker_a", "person_a", "defendant",
}
_INTERVIEWER_ROLES = {
    "interviewer", "officer", "agent", "clinician", "system", "operator", "investigator",
    "detective", "counselor", "therapist", "speaker_b", "person_b", "questioner",
}


def _normalize_role(role: str) -> str:
    if not role:
        return ""
    r = str(role).strip().lower().replace(" ", "_").replace("-", "_")
    if r in _SUBJECT_ROLES:
        return "subject"
    if r in _INTERVIEWER_ROLES:
        return "interviewer"
    # token/substring matching for common vendor labels (e.g., "Officer A", "Speaker 1")
    parts = set(r.split("_"))
    if parts & {"officer", "interviewer", "detective", "agent", "investigator", "operator", "clinician", "therapist", "counselor"}:
        return "interviewer"
    if parts & {"subject", "suspect", "witness", "respondent", "interviewee", "defendant", "deponent", "patient", "client"}:
        return "subject"
    return r


def canonicalize_turn(turn: Any) -> Dict[str, Any]:
    """Normalize a vendor-like/common transcript turn to canonical {role, text, ...metadata}.

    Accepts common aliases (speaker/role, text/utterance/content/body; timestamps/ids).
    Preserves recognized metadata and unknown keys (non-destructive). If a field cannot be
    mapped, returns best-effort dict; validation can reject invalid turns.
    """
    if not isinstance(turn, Mapping):
        if isinstance(turn, str):
            return {"role": "subject", "text": turn}
        return {"role": "", "text": ""}
    out: Dict[str, Any] = {}
    # role
    role = ""
    for k in _ROLE_KEYS:
        v = turn.get(k)
        if v is not None and str(v).strip():
            role = str(v).strip()
            break
    norm_role = _normalize_role(role)
    out["role"] = norm_role
    if role and norm_role in ("subject", "interviewer") and norm_role != str(role).strip().lower().replace(" ", "_").replace("-", "_"):
        out["speaker_original"] = role
    elif role and str(role).strip().lower().replace(" ", "_").replace("-", "_") not in ("subject", "interviewer") and norm_role in ("subject", "interviewer"):
        out["speaker_original"] = role
    # text
    text = ""
    for k in (*_TEXT_KEYS, "words", "tokens"):
        v = turn.get(k)
        if isinstance(v, str):
            text = v
            break
        if isinstance(v, list) and v and all(isinstance(x, (str, Mapping)) for x in v):
            parts = []
            for x in v:
                if isinstance(x, str):
                    parts.append(x)
                elif isinstance(x, Mapping):
                    w = x.get("text") or x.get("word") or x.get("token") or x.get("punctuated_word") or ""
                    if w is not None and str(w).strip():
                        parts.append(str(w))
            joined = " ".join(p for p in parts if p).strip()
            if joined:
                text = joined
                break
    out["text"] = text
    # metadata
    for k in _META_KEYS:
        if k in turn and turn[k] is not None:
            out[k] = turn[k]
    # preserve known feature containers and other useful keys
    for k in ("prosody", "acoustic", "audio_features", "features", "meta", "metadata",
              "response_latency_ms", "latency_ms", "delay_ms", "response_latency_s", "latency_s",
              "duration_ms", "speech_duration_ms", "duration_s", "speech_duration_s",
              "pause_total_ms", "pause_duration_ms", "silence_ms", "pause_count",
              "gaze_aversion_ratio", "blink_rate", "heart_rate_bpm", "hrv_ms", "hrv_rmssd_ms"):
        if k in turn and k not in out and turn[k] is not None:
            out[k] = turn[k]
    # keep any remaining simple scalar keys (non-destructive, avoid overwriting)
    for k, v in turn.items():
        if k in out:
            continue
        if k in _ROLE_KEYS or k in _TEXT_KEYS:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
    return out


def validate_transcript_turns(turns: Any) -> List[Dict[str, Any]]:
    """Validate and return canonicalized turns. Raises ValueError with clear messages on invalid input."""
    if turns is None:
        return []
    if isinstance(turns, (str, bytes)):
        raise ValueError("transcript must be a sequence of turns or a wrapper object, not a string")
    if isinstance(turns, Mapping):
        # allow wrapper pass-through if caller forgot normalization
        from .observations.runner import _normalize_transcript as _nt
        turns = _nt(turns)
    if not isinstance(turns, Sequence):
        raise ValueError(f"transcript must be a sequence of turns, got {type(turns).__name__}")
    out: List[Dict[str, Any]] = []
    for i, t in enumerate(turns):
        if t is None:
            continue
        ct = canonicalize_turn(t)
        # A turn is valid if it has any mappable content or is an explicit empty placeholder? Be permissive.
        if not isinstance(ct, dict):
            raise ValueError(f"turn[{i}] could not be normalized to a mapping")
        out.append(ct)
    return out


def normalize_transcript(source: Any) -> List[Dict[str, Any]]:
    """Normalize vendor/common transcript JSON shapes to canonical turns [{role,text,...}]."""
    if source is None:
        return []
    # if it's a raw JSON string/path/file, load it first? keep separate from load_transcript API.
    raw = source
    if isinstance(raw, (str, Path)):
        p = Path(raw)
        if p.exists() and p.is_file():
            raw = json.loads(p.read_text(encoding="utf-8"))
        else:
            s = str(raw)
            if s.lstrip().startswith(("{", "[")):
                raw = json.loads(s)
            else:
                raw = json.loads(Path(s).read_text(encoding="utf-8"))
    if hasattr(raw, "read"):
        raw = json.load(raw)
    turns = _normalize_transcript(raw)
    # also accept vendor wrappers
    if isinstance(raw, Mapping) and not turns:
        for key in ("utterances", "segments", "items", "entries", "results", "dialogue", "conversation"):
            v = raw.get(key)
            if isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
                turns = v
                break
    return validate_transcript_turns(turns)


def load_transcript(source: Union[str, Path, Mapping[str, Any], Sequence[Any], Any]) -> Any:
    """Load/normalize transcript JSON.

    Accepts: file path (str/Path), file-like object with .read(), JSON string,
    dict/list transcript structures (including wrappers with turns/transcript/messages).
    Vendor/common field aliases (speaker/text/timestamps) are normalized to canonical turns.
    """
    if source is None:
        return []
    try:
        return normalize_transcript(source)
    except Exception:
        # Backward-compat fallback to prior behavior
        if isinstance(source, (str, Path)):
            p = Path(source)
            if p.exists() and p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
            else:
                s = str(source)
                data = json.loads(s) if s.lstrip().startswith(("{", "[")) else json.loads(Path(s).read_text(encoding="utf-8"))
            return _normalize_transcript(data)
        if hasattr(source, "read"):
            data = json.load(source)
            return _normalize_transcript(data)
        return _normalize_transcript(source)


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
    raw = None
    source_name = None
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists() and p.is_file():
            source_name = str(p)
            raw = json.loads(p.read_text(encoding="utf-8"))
        else:
            try:
                raw = json.loads(str(source))
            except Exception:
                p = Path(str(source))
                raw = json.loads(p.read_text(encoding="utf-8"))
                source_name = str(p)
    elif hasattr(source, "read"):
        raw = json.load(source)
        source_name = getattr(source, "name", None)
    else:
        raw = source
    transcript = normalize_transcript(raw)
    r = runner or default_runner()
    pkg = r.build_package(transcript, session_id=session_id, annotations=annotations)
    if include_source_artifact:
        try:
            turn_count = len(list(transcript)) if transcript is not None else None
        except Exception:
            turn_count = None
        pkg["source_artifact"] = {
            "type": "transcript_json",
            "name": source_name,
            "transcript_sha256": transcript_source_hash(transcript),
            "turn_count": turn_count,
        }
    return pkg
