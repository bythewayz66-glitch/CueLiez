"""Minimal persistent training credential/record model (Phase 9.4).

This is technical record support (file-backed JSONL, tamper-evident hashes),
not a full LMS/certification authority. Observation/cue-only program scope;
never implies deception-detection, legal, or clinical certification.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .training import TrainingAcknowledgement, TrainingModule, validate_training_ack

try:
    from ..audit import audit_event
except Exception:  # pragma: no cover
    def audit_event(*args: Any, **kwargs: Any) -> dict:  # type: ignore[no-redef]
        return {}

DEFAULT_RECORDS_PATH = Path("cueliez_training_records.jsonl")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash_record(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "record_hash"}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


@dataclass
class TrainingCredentialRecord:
    credential_id: str
    operator_id: str
    module_id: str
    module_version: str
    status: str = "active"  # active | revoked | expired | suspended
    issued_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    issued_by: Optional[str] = None
    assessment_passed: bool = False
    completed_topics: List[str] = field(default_factory=list)
    notes: str = ""
    record_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["record_hash"] = _hash_record(d)
        return d

    def is_valid_now(self, now: Optional[float] = None) -> bool:
        t = time.time() if now is None else now
        if self.status != "active":
            return False
        if self.expires_at is not None and t > float(self.expires_at):
            return False
        return bool(self.assessment_passed and (self.operator_id or "").strip())

    def to_ack(self) -> TrainingAcknowledgement:
        return TrainingAcknowledgement(
            module_id=self.module_id,
            module_version=self.module_version,
            operator_id=self.operator_id,
            attested_by=self.issued_by,
            completed_topics=list(self.completed_topics or []),
            assessment_passed=bool(self.assessment_passed),
            acknowledged_at=self.issued_at,
            notes=self.notes or f"credential:{self.credential_id}",
        )


class TrainingRecordStore:
    """Append-only JSONL store for training credential events/records."""

    def __init__(self, path: str | Path = DEFAULT_RECORDS_PATH, *, enforce_rbac: Optional[bool] = None, admin_actors: Optional[list[str]] = None):
        import os
        self.path = Path(path)
        if enforce_rbac is None:
            enforce_rbac = os.environ.get("CUELIEZ_TRAINING_ENFORCE_RBAC", "").strip().lower() in {"1", "true", "yes", "on"}
        self.enforce_rbac = bool(enforce_rbac)
        if admin_actors is None:
            raw = os.environ.get("CUELIEZ_TRAINING_ADMIN_ACTORS", "")
            admin_actors = [x.strip() for x in raw.split(",") if x.strip()]
        self.admin_actors = list(admin_actors)

    def _check_admin(self, action: str, actor: Optional[str]) -> str:
        who = (actor or "").strip()
        if self.enforce_rbac and not who:
            raise PermissionError(f"training_{action}_actor_required")
        if self.enforce_rbac and self.admin_actors and who not in self.admin_actors:
            raise PermissionError(f"training_{action}_forbidden")
        return who

    def _append(self, event: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload.setdefault("ts", time.time())
        payload["event_hash"] = _hash_record(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_canonical(payload) + "\n")

    def issue(
        self,
        module: TrainingModule,
        ack: TrainingAcknowledgement,
        *,
        issued_by: Optional[str] = None,
        expires_at: Optional[float] = None,
        status: str = "active",
        actor: Optional[str] = None,
    ) -> TrainingCredentialRecord:
        who = self._check_admin("issue", actor or issued_by or ack.attested_by)
        result = validate_training_ack(module, ack)
        if not result.get("valid"):
            raise ValueError(f"invalid_training_ack: {result.get('notes')}")
        rec = TrainingCredentialRecord(
            credential_id=str(uuid.uuid4()),
            operator_id=(ack.operator_id or "").strip(),
            module_id=module.id,
            module_version=module.version,
            status=status,
            expires_at=expires_at,
            issued_by=issued_by or ack.attested_by or (who or None),
            assessment_passed=bool(ack.assessment_passed),
            completed_topics=list(ack.completed_topics or module.required_topics),
            notes=ack.notes or "",
        )
        self._append({"type": "issue", "actor": who or None, "credential": rec.to_dict()})
        audit_event("training.issue", details={"credential_id": rec.credential_id, "operator_id": rec.operator_id, "module_id": rec.module_id, "actor": who or None})
        return rec

    def revoke(self, credential_id: str, *, by: Optional[str] = None, reason: str = "", actor: Optional[str] = None) -> None:
        who = self._check_admin("revoke", actor or by)
        self._append({"type": "revoke", "credential_id": credential_id, "by": by or (who or None), "actor": who or None, "reason": reason, "status": "revoked"})
        audit_event("training.revoke", details={"credential_id": credential_id, "actor": who or None, "reason": reason})

    def _events(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def get(self, credential_id: str) -> Optional[TrainingCredentialRecord]:
        current = None
        for ev in self._events():
            if ev.get("type") == "issue":
                c = (ev.get("credential") or {})
                if c.get("credential_id") == credential_id:
                    c = dict(c)
                    c.pop("record_hash", None)
                    current = TrainingCredentialRecord(**c)
            elif ev.get("type") == "revoke" and ev.get("credential_id") == credential_id and current:
                current.status = "revoked"
        return current

    def verify(self, credential_id: str, *, now: Optional[float] = None) -> Dict[str, Any]:
        rec = self.get(credential_id)
        if not rec:
            return {"ok": False, "reason": "not_found", "credential_id": credential_id}
        return {"ok": rec.is_valid_now(now=now), "credential_id": credential_id, "status": rec.status, "operator_id": rec.operator_id, "module_id": rec.module_id, "module_version": rec.module_version, "expires_at": rec.expires_at}

    def ack_for_gate(self, credential_id: str, *, now: Optional[float] = None) -> TrainingAcknowledgement:
        rec = self.get(credential_id)
        if not rec:
            raise ValueError("credential_not_found")
        if not rec.is_valid_now(now=now):
            raise ValueError(f"credential_not_valid:{rec.status}")
        return rec.to_ack()
