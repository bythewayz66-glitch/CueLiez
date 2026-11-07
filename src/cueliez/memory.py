"""Trusted memory substrate for CueLiez sealed observations.

Adapted from mem20-ce invariants:
- grounded vs simulated partitions
- contamination controls
- sealed packages are observed indicators, not findings
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class ContaminationError(Exception):
    pass


class PartitionError(Exception):
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryEngine:
    def __init__(self, store_path: str | Path = "~/.cueliez/store"):
        self.store_path = Path(os.path.expanduser(str(store_path))).resolve()
        self.store_path.mkdir(parents=True, exist_ok=True)
        (self.store_path / "grounded").mkdir(exist_ok=True)
        (self.store_path / "simulated").mkdir(exist_ok=True)
        self.ledger_path = self.store_path / "ledger.jsonl"
        self._grounded_ids: set[str] = set()
        self._simulated_ids: set[str] = set()

    def remember_observation(
        self,
        content: str,
        *,
        tags: Optional[Sequence[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a grounded observed indicator (not a finding)."""
        rid = str(uuid.uuid4())
        record = Record(
            id=rid,
            content=content,
            origin="grounded",
            tags=list(tags or []) + ["cueliez", "observation"],
            epistemic_status="observed_indicator",
            evidence=evidence,
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
