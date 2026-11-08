"""CueLiez — Legal Interview Engine (system package).

Observation and cue support for legal interviews. Not a lie detector.
"""

__version__ = "0.2.0"

from .gates import (
    DISCLAIMER,
    DISCLAIMER_VERSION,
    GateError,
    SessionGateState,
    assert_not_sealed,
    check_prohibited_uses,
    compute_package_hash,
    custody_receipt,
    export_sealed_package_json,
    extract_high_priority_cue_ids,
    is_sealed,
    package_completeness,
    record_consent,
    seal_observation_package,
    sign_package,
    verify_package_hash,
)
from .session import assert_can_observe, seal, start_session
from .memory import MemoryEngine
from .observations import ObservationRunner, default_runner, full_runner
from .packs import CuePack, get_pack, list_packs
from .delivery import (
    AudioCueRenderer,
    CueEvent,
    OFFICER_CUE_NOTES_KEY,
    OfficerCueNote,
    OnscreenCueRenderer,
    attach_officer_cue_notes,
    cues_from_observations,
    generate_tone_wav,
    normalize_officer_cue_notes,
)
from .export import export_package_json, export_sealed_package, render_package_summary_html, render_package_summary_markdown
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
    "DISCLAIMER_VERSION",
    "GateError",
    "SessionGateState",
    "assert_can_observe",
    "assert_not_sealed",
    "check_prohibited_uses",
    "compute_package_hash",
    "custody_receipt",
    "export_sealed_package_json",
    "extract_high_priority_cue_ids",
    "is_sealed",
    "package_completeness",
    "record_consent",
    "seal",
    "seal_observation_package",
    "sign_package",
    "start_session",
    "verify_package_hash",
    "MemoryEngine",
    "ObservationRunner",
    "default_runner",
    "full_runner",
    "CuePack",
    "get_pack",
    "list_packs",
    "AudioCueRenderer",
    "CueEvent",
    "OFFICER_CUE_NOTES_KEY",
    "OfficerCueNote",
    "OnscreenCueRenderer",
    "attach_officer_cue_notes",
    "cues_from_observations",
    "generate_tone_wav",
    "normalize_officer_cue_notes",
    "export_package_json",
    "export_sealed_package",
    "render_package_summary_html",
    "render_package_summary_markdown",
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
