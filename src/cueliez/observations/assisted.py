"""Feature-flagged ML/LLM-assisted observer interfaces (prototype, DISABLED).

No external ML calls. Not wired into default_runner/full_runner/packs.
Production path remains rule/heuristic unless explicitly enabled under approved controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .base import ObservationResult

# Feature flag: must remain False in production/default builds.
ASSISTED_OBSERVERS_ENABLED = False


@dataclass(frozen=True)
class AssistedModelProvenance:
    provider: str
    model: str
    version: str
    adapter_version: str = "v0"
    prompt_hash: str = ""

    @property
    def model_id(self) -> str:
        base = f"{self.provider}/{self.model}@{self.version}#{self.adapter_version}"
        return f"{base}+{self.prompt_hash}" if self.prompt_hash else base


class AssistedObserverPrototype:
    """Base for future assisted observers. Disabled by default; no network/ML execution."""

    method_id = "cueliez.observations.assisted.prototype/v0"
    enabled_flag_name = "ASSISTED_OBSERVERS_ENABLED"

    def is_enabled(self) -> bool:
        return bool(ASSISTED_OBSERVERS_ENABLED)

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        # Fail closed: no external calls; emit nothing unless explicitly enabled and implemented.
        result = ObservationResult(method=self.method_id)
        if not self.is_enabled():
            result.notes.append("assisted_observers_disabled")
            return result
        result.notes.append("assisted_observer_not_implemented")
        return result
