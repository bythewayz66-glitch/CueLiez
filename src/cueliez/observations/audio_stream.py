"""Real-time audio stream hook (consent-governed, gated by default).

Consumes derived audio feature metadata chunks (no raw audio) and surfaces cues
as turns arrive. Off by default; requires modality consent + jurisdiction.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .audio_path import AUDIO_FEATURE_OBSERVERS, observe_audio_features
from .modality_gates import check_modality_allowed


class AudioStreamHook:
    """Accumulate derived audio-feature turns and emit cues incrementally."""

    def __init__(self, *, state: Any = None, require_consent_check: bool = True):
        self.state = state
        self.require_consent_check = require_consent_check
        self._turns: List[Dict[str, Any]] = []
        self._seen_cue_ids: set = set()

    def push_turn(self, turn: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Append a derived-feature turn and return newly surfaced cue dicts."""
        if self.require_consent_check:
            check_modality_allowed(self.state, "audio_features")
        self._turns.append(dict(turn))
        all_obs = observe_audio_features(self._turns, state=self.state, require_consent_check=False)
        new = []
        for o in all_obs:
            cid = o.get("cue_id")
            if cid and cid in self._seen_cue_ids:
                continue
            if cid:
                self._seen_cue_ids.add(cid)
            new.append(o)
        return new

    def all_turns(self) -> List[Dict[str, Any]]:
        return list(self._turns)

    def reset(self) -> None:
        self._turns.clear()
        self._seen_cue_ids.clear()

def stream_audio_features(
    chunks,
    *,
    state=None,
    require_consent_check=True,
):
    hook = AudioStreamHook(state=state, require_consent_check=require_consent_check)
    out = []
    for c in chunks:
        out.extend(hook.push_turn(c))
    return out
