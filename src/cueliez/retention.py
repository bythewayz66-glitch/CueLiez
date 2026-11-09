"""Retention and privacy helpers for sealed packages."""
from __future__ import annotations
import copy, time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

DEFAULT_RETENTION_SECONDS = {
    "government": 365*24*3600*7, "interrogation": 365*24*3600*5,
    "clinical": 365*24*3600*7, "therapy": 365*24*3600*7, "generic": 365*24*3600*3,
}

@dataclass
class RetentionPolicy:
    mode: str = "generic"
    retain_until: Optional[float] = None
    jurisdiction: Optional[str] = None
    notes: str = ""
    redactable_fields: Set[str] = field(default_factory=lambda: {"subject_id", "operator_notes_raw", "raw_transcript", "audio_paths"})
    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.retain_until is None: return False
        return (now if now is not None else time.time()) > self.retain_until
    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode, "retain_until": self.retain_until, "jurisdiction": self.jurisdiction,
                "notes": self.notes, "redactable_fields": sorted(self.redactable_fields)}

def derive_retention_policy(package: Dict[str, Any], *, custom_seconds: Optional[Dict[str, int]] = None) -> RetentionPolicy:
    gs = package.get("gate_state") if isinstance(package.get("gate_state"), dict) else {}
    mode = str(gs.get("mode") or package.get("mode") or "generic").lower()
    sealed_at = package.get("sealed_at")
    try: sealed_ts = float(sealed_at) if sealed_at is not None else time.time()
    except (TypeError, ValueError): sealed_ts = time.time()
    table = dict(DEFAULT_RETENTION_SECONDS)
    if custom_seconds: table.update(custom_seconds)
    window = table.get(mode, table["generic"])
    return RetentionPolicy(mode=mode, retain_until=sealed_ts + window, jurisdiction=gs.get("jurisdiction"),
                           notes="Derived from mode defaults; operator must confirm jurisdiction rules.")

def check_retention(package: Dict[str, Any], *, now: Optional[float] = None) -> Dict[str, Any]:
    policy = derive_retention_policy(package)
    expired = policy.is_expired(now)
    return {"ok": True, "expired": expired, "policy": policy.to_dict(),
            "guidance": ("Retention window elapsed under derived policy. Follow jurisdiction/legal hold — do not auto-delete."
                         if expired else "Within derived retention window. Maintain chain of custody.")}

def redact_for_secondary_sharing(package: Dict[str, Any], *, extra_fields: Optional[Set[str]] = None) -> Dict[str, Any]:
    protected = {"package_hash", "content_hash", "package_signature", "epistemic_status", "is_definitive_finding",
                 "origin", "disclaimer", "disclaimer_version", "schema_version", "product", "product_version", "sealed_at", "sealed"}
    policy = derive_retention_policy(package)
    targets = set(policy.redactable_fields) | (set(extra_fields) if extra_fields else set())
    out = copy.deepcopy(package)
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k in protected: continue
                if k in targets: obj[k] = "[REDACTED]"
                else: obj[k] = _walk(v)
        elif isinstance(obj, list):
            return [_walk(x) for x in obj]
        return obj
    return _walk(out)
