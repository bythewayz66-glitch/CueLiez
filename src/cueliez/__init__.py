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
from .observations import ObservationRunner, default_runner

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
]

# Language: observation and cues — never lie detection.
