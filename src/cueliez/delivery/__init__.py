"""Professional cue delivery: onscreen and audio outputs.

Transforms observations into non-verdict cues for human professionals.
"""

from .audio import AudioCueRenderer, generate_tone_wav
from .events import CueEvent, cues_from_observations
from .notes import (
    OFFICER_CUE_NOTES_KEY,
    OfficerCueNote,
    attach_officer_cue_notes,
    normalize_officer_cue_notes,
    notes_by_cue_id,
)
from .onscreen import OnscreenCueRenderer
from .dashboard import LiveDashboardServer

__all__ = [
    "AudioCueRenderer",
    "generate_tone_wav",
    "CueEvent",
    "cues_from_observations",
    "OnscreenCueRenderer",
    "LiveDashboardServer",
    "OFFICER_CUE_NOTES_KEY",
    "OfficerCueNote",
    "attach_officer_cue_notes",
    "normalize_officer_cue_notes",
    "notes_by_cue_id",
]
