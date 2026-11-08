"""Stable transcript ingest contract (Phase 7). Observation/cue workflow input only.

Loads transcript JSON from supported sources and can attach neutral source-artifact
metadata (original artifact reference) to an observation package before seal.
No findings/verdicts. Sealed packages remain the attachable artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union

from .observations.runner import ObservationRunner, _normalize_transcript, default_runner


def load_transcript(source: Union[str, Path, Mapping[str, Any], Sequence[Any], Any]) -> Any:
    """Load/normalize transcript JSON.

    Accepts: file path (str/Path), file-like object with .read(), JSON string,
    dict/list transcript structures (including wrappers with turns/transcript/messages).
    """
    if source is None:
        return []
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
            raw = json.loads(str(source))
    elif hasattr(source, "read"):
        raw = json.load(source)
        source_name = getattr(source, "name", None)
    else:
        raw = source
    transcript = _normalize_transcript(raw)
    r = runner or default_runner()
    pkg = r.build_package(transcript, session_id=session_id, annotations=annotations)
    if include_source_artifact:
        pkg["source_artifact"] = {
            "type": "transcript_json",
            "name": source_name,
            "transcript_sha256": transcript_source_hash(transcript),
            "turn_count": len(list(transcript)) if hasattr(transcript, "__len__") else None,
        }
    return pkg
