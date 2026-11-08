"""Officer cue notes and actions for delivery surfaces.

Notes are human-authored responses to observation cues. They are not findings
and must be preserved in sealed packages when present.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    from ..gates import GateError, assert_not_sealed, is_sealed
except Exception:  # pragma: no cover
    def is_sealed(package):  # type: ignore[no-redef]
        return bool(isinstance(package, Mapping) and (package.get("sealed_at") or package.get("package_hash") or package.get("sealed") is True))

    def assert_not_sealed(package, action="mutate package"):  # type: ignore[no-redef]
        if is_sealed(package):
            raise ValueError(f"Cannot {action}: package is already sealed.")

OFFICER_CUE_NOTES_KEY = "officer_cue_notes"
ALLOWED_ACTIONS = frozenset({"acknowledged", "dismissed", "noted", "responded"})


@dataclass
class OfficerCueNote:
    """A human note/action on a specific cue."""

    cue_id: str
    action: str = "noted"
    note: str = ""
    priority: Optional[str] = None
    officer_id: Optional[str] = None
    turn_index: Optional[int] = None
    label: Optional[str] = None
    recorded_at: float = field(default_factory=time.time)

    def normalized(self) -> "OfficerCueNote":
        action = (self.action or "noted").strip().lower()
        if action not in ALLOWED_ACTIONS:
            action = "noted"
        return OfficerCueNote(
            cue_id=str(self.cue_id or "").strip(),
            action=action,
            note=str(self.note or "").strip(),
            priority=(str(self.priority).strip().lower() if self.priority else None),
            officer_id=(str(self.officer_id).strip() if self.officer_id else None),
            turn_index=int(self.turn_index) if isinstance(self.turn_index, int) and not isinstance(self.turn_index, bool) else None,
            label=(str(self.label).strip() if self.label else None),
            recorded_at=float(self.recorded_at),
        )

    def to_dict(self) -> Dict[str, Any]:
        n = self.normalized()
        d = asdict(n)
        return {k: v for k, v in d.items() if v is not None and v != ""}


def normalize_officer_cue_notes(notes: Optional[Sequence[Mapping[str, Any] | OfficerCueNote]]) -> List[Dict[str, Any]]:
    """Normalize officer cue notes to JSON-safe package records."""
    if not notes:
        return []
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in notes:
        if isinstance(item, OfficerCueNote):
            rec = item.normalized().to_dict()
        elif isinstance(item, Mapping):
            rec = OfficerCueNote(
                cue_id=str(item.get("cue_id") or ""),
                action=str(item.get("action") or "noted"),
                note=str(item.get("note") or ""),
                priority=item.get("priority"),
                officer_id=item.get("officer_id"),
                turn_index=item.get("turn_index"),
                label=item.get("label"),
                recorded_at=float(item.get("recorded_at") or time.time()),
            ).normalized().to_dict()
        else:
            continue
        cue_id = rec.get("cue_id")
        if not cue_id:
            continue
        # keep latest note per cue_id+action+timestamp bucket lightly by allowing multiples? 
        # preserve all meaningful records in order; dedupe exact duplicates only.
        key = (cue_id, rec.get("action"), rec.get("note"), rec.get("recorded_at"))
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def attach_officer_cue_notes(
    package: Mapping[str, Any],
    notes: Optional[Sequence[Mapping[str, Any] | OfficerCueNote]],
    *,
    replace: bool = False,
) -> Dict[str, Any]:
    """Return a package copy with normalized officer cue notes attached.

    Notes must be attached before seal. Iceman seal/hashing preserves `officer_cue_notes`.
    """
    try:
        assert_not_sealed(package)
    except TypeError:
        try:
            assert_not_sealed(package, "attach officer cue notes")
        except GateError as e:
            raise ValueError(str(e)) from e
    except GateError as e:
        raise ValueError(str(e)) from e
    if is_sealed(package):
        raise ValueError("Cannot attach officer cue notes to a sealed package. Attach notes before seal.")
    out = dict(package)
    new_notes = normalize_officer_cue_notes(notes)
    if replace or OFFICER_CUE_NOTES_KEY not in out or not isinstance(out.get(OFFICER_CUE_NOTES_KEY), list):
        out[OFFICER_CUE_NOTES_KEY] = new_notes
    else:
        existing = normalize_officer_cue_notes(out.get(OFFICER_CUE_NOTES_KEY))
        out[OFFICER_CUE_NOTES_KEY] = existing + [n for n in new_notes if n not in existing]
    return out


def notes_by_cue_id(notes: Optional[Sequence[Mapping[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    idx: Dict[str, List[Dict[str, Any]]] = {}
    for n in normalize_officer_cue_notes(notes):
        cid = n.get("cue_id")
        if cid:
            idx.setdefault(cid, []).append(n)
    return idx
