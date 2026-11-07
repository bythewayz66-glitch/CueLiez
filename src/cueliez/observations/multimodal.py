"""Cross-modal observation helpers.

Convergence across independent observation categories can be a cue to review the
same turn/context more carefully. It is NOT a deception determination or score.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Sequence

from .base import ObservationResult, clamp01, make_observation


class CrossModalConvergenceObserver:
    """Operates on already-produced observation dicts (post-run).

    Use via `observe_observations(observations)`; the standard `observe(transcript)`
    method returns no observations because it needs prior modality outputs.
    """

    method_id = "cueliez.observations.multimodal.convergence/v1"

    def observe(self, transcript: Sequence[Mapping[str, Any]]) -> ObservationResult:
        res = ObservationResult(method=self.method_id)
        res.notes.append("requires_observation_inputs")
        return res

    def observe_observations(self, observations: Sequence[Mapping[str, Any]], *, min_categories: int = 2) -> ObservationResult:
        result = ObservationResult(method=self.method_id)
        by_turn: defaultdict[int, set[str]] = defaultdict(set)
        for o in observations:
            ti = o.get("turn_index")
            if ti is None:
                continue
            cat = str(o.get("category") or "")
            if cat and cat not in {"multimodal"}:
                by_turn[int(ti)].add(cat)
        for turn_index, cats in sorted(by_turn.items()):
            if len(cats) < min_categories:
                continue
            score = clamp01(0.3 + 0.12 * min(len(cats), 5))
            result.observations.append(make_observation(
                label="multi_indicator_convergence_observed",
                score=score,
                method_id=self.method_id,
                category="multimodal",
                evidence={"turn_index": turn_index, "categories": sorted(cats), "category_count": len(cats)},
                cue="Independent observation categories converged on the same turn; review context carefully. This is not a determination.",
                turn_index=turn_index,
            ))
        return result


def add_convergence_observations(observations: List[Dict[str, Any]], *, min_categories: int = 2) -> List[Dict[str, Any]]:
    conv = CrossModalConvergenceObserver().observe_observations(observations, min_categories=min_categories)
    return observations + conv.to_dicts()
