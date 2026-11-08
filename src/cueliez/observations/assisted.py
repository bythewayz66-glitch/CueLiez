"""Feature-flagged ML/LLM-assisted observer interfaces (Phase 1 implementation, DISABLED by default).

No external ML calls in default/production path. Not wired into default_runner/full_runner/packs.
Assisted adapters may be registered only for explicitly enabled, approved deployments.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Sequence

from .base import ObservationResult

# Feature flag: default OFF. Enable only via explicit deployment config (approved/on-prem controls).
ASSISTED_OBSERVERS_ENABLED = os.environ.get("CUELIEZ_ASSISTED_OBSERVERS", "").strip() == "1"


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


AssistedAdapter = Callable[[Sequence[Mapping[str, Any]]], ObservationResult]
_REGISTRY: List[tuple[str, AssistedAdapter, AssistedModelProvenance | None]] = []


def register_assisted_observer(name: str, adapter: AssistedAdapter, provenance: AssistedModelProvenance | None = None) -> None:
    """Register an assisted adapter (deployment-time). No effect unless feature flag is enabled."""
    if not name or not callable(adapter):
        raise ValueError("name and callable adapter required")
    _REGISTRY.append((str(name), adapter, provenance))


def clear_assisted_registry() -> None:
    _REGISTRY.clear()


def make_multi_signal_assisted_adapter():
    """Factory for a deterministic, no-external-ML assisted adapter.

    Combines hedging + vagueness + distancing markers into a single multi-signal
    cue when at least two distinct marker families are present on one turn.
    No network/ML calls; safe to register only in approved deployments.
    """
    from .linguistic import (
        HEDGE_PATTERNS,
        VAGUE_PATTERNS,
        DISTANCING_PATTERNS,
        _count_patterns,
        _words,
    )

    def adapter(transcript):
        result = ObservationResult(method="cueliez.observations.assisted.multi_signal/v1")
        for i, turn in enumerate(transcript):
            try:
                from .base import is_subject_turn, text_of, source_span
            except Exception:
                continue
            if not is_subject_turn(turn):
                continue
            text = text_of(turn)
            words = _words(text)
            if len(words) < 6:
                continue
            hc, hf = _count_patterns(text, HEDGE_PATTERNS)
            vc, vf = _count_patterns(text, VAGUE_PATTERNS)
            dc, df = _count_patterns(text, DISTANCING_PATTERNS)
            families = sum(1 for c in (hc, vc, dc) if c > 0)
            if families < 2:
                continue
            score = min(1.0, 0.4 + 0.12 * families + 0.02 * (hc + vc + dc))
            from .base import make_observation
            ev = {
                "hedge_count": hc,
                "vague_count": vc,
                "distancing_count": dc,
                "families": families,
                "word_count": len(words),
            }
            ev.update(source_span(turn, i))
            result.observations.append(make_observation(
                label="multi_signal_language_pattern",
                score=score,
                method_id="cueliez.observations.assisted.multi_signal/v1",
                category="linguistic",
                evidence=ev,
                cue="Multiple linguistic marker families appear in one response; consider probing for specifics.",
                turn_index=i,
                priority="normal",
            ))
        return result

    return adapter


def run_assisted_observers(transcript: Sequence[Mapping[str, Any]], *, enabled: bool | None = None) -> List[ObservationResult]:
    """Run registered assisted adapters only when explicitly enabled. Default: empty (no external ML)."""
    on = ASSISTED_OBSERVERS_ENABLED if enabled is None else bool(enabled)
    if not on or not _REGISTRY:
        return []
    out: List[ObservationResult] = []
    for _name, adapter, _prov in list(_REGISTRY):
        try:
            res = adapter(transcript)
            if isinstance(res, ObservationResult):
                out.append(res)
        except Exception:
            # Fail closed for assisted path: do not break rule-based observation run.
            continue
    return out


def merge_assisted_observations(
    observations: List[Dict[str, Any]],
    transcript: Sequence[Mapping[str, Any]],
    *,
    enabled: bool | None = None,
) -> List[Dict[str, Any]]:
    """Opt-in merge of assisted observations (default off). Additive; no external ML by default."""
    results = run_assisted_observers(transcript, enabled=enabled)
    out = list(observations)
    for r in results:
        out.extend(r.to_dicts())
    return out
