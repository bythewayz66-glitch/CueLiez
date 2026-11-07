"""CueLiez — Legal Interview Engine (system package).

Observation and cue support for legal interviews. Not a lie detector.
"""

__version__ = "0.2.0"

from .gates import (
    DISCLAIMER,
    GateError,
    SessionGateState,
    record_consent,
    seal_observation_package,
)
from .memory import MemoryEngine
from .observations import ObservationRunner, default_runner, full_runner
from .packs import CuePack, get_pack, list_packs
from .delivery import AudioCueRenderer, CueEvent, OnscreenCueRenderer, cues_from_observations, generate_tone_wav
from .consent import (
    ConsentAcknowledgement,
    ConsentRecord,
    apply_consent_to_gate_state,
    general_consent_form,
    get_consent_bundle,
    validate_acknowledgement,
)
from .compliance import (
    apply_training_to_gate_state,
    domain_disclaimer,
    domain_training,
    get_disclaimer_bundle,
    get_training_bundle,
)

__all__ = [
    "__version__",
    "DISCLAIMER",
    "GateError",
    "SessionGateState",
    "record_consent",
    "seal_observation_package",
    "MemoryEngine",
    "ObservationRunner",
    "default_runner",
    "full_runner",
    "CuePack",
    "get_pack",
    "list_packs",
    "AudioCueRenderer",
    "CueEvent",
    "OnscreenCueRenderer",
    "cues_from_observations",
    "generate_tone_wav",
    "ConsentAcknowledgement",
    "ConsentRecord",
    "apply_consent_to_gate_state",
    "general_consent_form",
    "get_consent_bundle",
    "validate_acknowledgement",
    "apply_training_to_gate_state",
    "domain_disclaimer",
    "domain_training",
    "get_disclaimer_bundle",
    "get_training_bundle",
]

# Language: observation and cues — never lie detection.
