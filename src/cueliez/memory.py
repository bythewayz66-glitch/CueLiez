"""Trusted memory substrate for CueLiez sealed observations.

Hardened write path:
- only observed_indicator may enter grounded observation store
- findings / verdict epistemic labels refused
- ledger append + partition file for every seal
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ALLOWED_GROUNDED_EPISTEMIC = frozenset({
    "observed_indicator",
    "observation",
    "indicator",
})

FORBIDDEN_EPISTEMIC = frozenset({
    "legal_finding",
    "diagnosis",
    "deception_confirmed",
    "fact_finding",
    "verdict",
    "guilty",
    "lie",
})


class ContaminationError(Exception):
    pass


class PartitionError(Exception):
    pass


class SealError(Exception):
    pass


@dataclass
class Record:
    id: str
    content: str
    origin: str  # grounded | simulated
    tags: List[str] = field(default_factory=list)
    epistemic_status: str = "observed_indicator"
    created_at: float = field(default_factory=time.time)
    evidence: Optional[Dict[str, Any]] = None
    disclaimer: Optional[str] = None
    sealed_package_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryEngine:
    def __init__(self, store_path: str | Path = "~/.cueliez/store"):
        self.store_path = Path(os.path.expanduser(str(store_path))).resolve()
        self.store_path.mkdir(parents=True, exist_ok=True)
        (self.store_path / "grounded").mkdir(exist_ok=True)
        (self.store_path / "simulated").mkdir(exist_ok=True)
        (self.store_path / "seals").mkdir(exist_ok=True)
        self.ledger_path = self.store_path / "ledger.jsonl"
        self._grounded_ids: set[str] = set()
        self._simulated_ids: set[str] = set()

    def _assert_observation_epistemic(self, epistemic_status: str) -> None:
        key = (epistemic_status or "").strip().lower()
        if key in FORBIDDEN_EPISTEMIC:
            raise ContaminationError(
                f"Refused epistemic_status={epistemic_status!r}: findings cannot enter the store."
            )
        if key not in ALLOWED_GROUNDED_EPISTEMIC:
            raise ContaminationError(
                f"Refused epistemic_status={epistemic_status!r}: "
                f"grounded writes must be one of {sorted(ALLOWED_GROUNDED_EPISTEMIC)}."
            )

    def remember_observation(
        self,
        content: str,
        *,
        tags: Optional[Sequence[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        epistemic_status: str = "observed_indicator",
        disclaimer: Optional[str] = None,
    ) -> str:
        """Store a grounded observed indicator (not a finding)."""
        self._assert_observation_epistemic(epistemic_status)
        rid = str(uuid.uuid4())
        record = Record(
            id=rid,
            content=content,
            origin="grounded",
            tags=list(tags or []) + ["cueliez", "observation"],
            epistemic_status="observed_indicator",
            evidence=evidence,
            disclaimer=disclaimer,
        )
        if record.origin != "grounded":
            raise ContaminationError("observations seal as grounded indicators only")
        entry = record.to_dict()
        entry["op"] = "remember_observation"
        entry["ts"] = time.time()
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        path = self.store_path / "grounded" / f"{rid}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)
        self._grounded_ids.add(rid)
        return rid

    def seal_package(self, package: Dict[str, Any]) -> str:
        """
        Persist a gate-hardened seal package.
        Caller must run gates.seal_observation_package first.
        """
        if not isinstance(package, dict):
            raise SealError("package must be a dict")
        if package.get("is_definitive_finding") is True:
            raise ContaminationError("cannot persist definitive findings")
        if package.get("epistemic_status") != "observed_indicator":
            raise ContaminationError("sealed package epistemic_status must be observed_indicator")
        if package.get("origin") != "grounded":
            raise ContaminationError("sealed package origin must be grounded")
        if not package.get("disclaimer"):
            raise SealError("sealed package must carry disclaimer")
        if package.get("firewall", {}).get("contamination_check") != "passed":
            raise SealError("package firewall.contamination_check must be passed")

        seal_id = str(uuid.uuid4())
        package = dict(package)
        package["seal_id"] = seal_id
        package["persisted_at"] = time.time()

        path = self.store_path / "seals" / f"{seal_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, ensure_ascii=False)

        # Also ledger a pointer record (observation, not finding)
        self.remember_observation(
            content=f"sealed_session:{seal_id}",
            tags=["cueliez", "seal", "session"],
            evidence={"seal_id": seal_id, "observation_count": len(package.get("observations") or [])},
            disclaimer=package.get("disclaimer"),
        )
        return seal_id
