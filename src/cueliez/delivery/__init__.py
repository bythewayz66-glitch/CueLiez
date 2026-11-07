"""Professional cue delivery: onscreen and audio outputs.

Transforms observations into non-verdict cues for human professionals.
"""

from .audio import AudioCueRenderer, generate_tone_wav
from .events import CueEvent, cues_from_observations
from .onscreen import OnscreenCueRenderer

__all__ = [
    "AudioCueRenderer",
    "generate_tone_wav",
    "CueEvent",
    "cues_from_observations",
    "OnscreenCueRenderer",
]
