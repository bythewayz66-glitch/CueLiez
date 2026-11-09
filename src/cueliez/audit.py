"""Structured, redacted audit logging for sensitive operations (Phase 9.3).

Observation/cue-system audit events only. Never log secrets, tokens, raw
credentials, or full sensitive content unnecessarily. Events are JSON lines.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional

_LOCK = threading.Lock()
_LOCAL = threading.local()
_REDACT_KEYS = {
    "token", "authorization", "auth", "password", "secret", "api_key", "apikey",
    "cookie", "set-cookie", "cuELIEZ_CONNECTOR_TOKEN".lower(), "bearer",
}


def set_audit_correlation_id(correlation_id: Optional[str]) -> None:
    _LOCAL.correlation_id = correlation_id


def get_audit_correlation_id() -> Optional[str]:
    return getattr(_LOCAL, "correlation_id", None)


def _redact(obj: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[redacted-depth]"
    if isinstance(obj, Mapping):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in _REDACT_KEYS or "token" in lk or "secret" in lk or "password" in lk:
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact(v, depth=depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_redact(v, depth=depth + 1) for v in obj]
    if isinstance(obj, str) and len(obj) > 500:
        return obj[:500] + "…[truncated]"
    return obj


def audit_event(
    event: str,
    *,
    outcome: str = "ok",
    details: Optional[Mapping[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> dict:
    """Emit a redacted JSON audit event. Best-effort; never raises to callers."""
    payload = {
        "ts": time.time(),
        "event": str(event),
        "outcome": str(outcome),
        "correlation_id": correlation_id if correlation_id is not None else get_audit_correlation_id(),
        "details": _redact(dict(details or {})),
    }
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    target = os.environ.get("CUELIEZ_AUDIT_LOG", "").strip()
    try:
        with _LOCK:
            if target:
                p = Path(target)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            elif os.environ.get("CUELIEZ_AUDIT_STDERR", "").strip().lower() in {"1", "true", "yes", "on"}:
                sys.stderr.write(line + "\n")
    except Exception:
        # Audit logging must not break primary operations.
        pass
    return payload
