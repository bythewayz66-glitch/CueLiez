"""Consent forms, domain supplements, and gate integration for CueLiez."""

from .forms import (
    ConsentAcknowledgement,
    ConsentDisclosure,
    ConsentForm,
    ConsentRecord,
    apply_consent_to_gate_state,
    domain_supplement,
    general_consent_form,
    get_consent_bundle,
    render_consent_form,
    validate_acknowledgement,
)

__all__ = [
    "ConsentAcknowledgement",
    "ConsentDisclosure",
    "ConsentForm",
    "ConsentRecord",
    "apply_consent_to_gate_state",
    "domain_supplement",
    "general_consent_form",
    "get_consent_bundle",
    "render_consent_form",
    "validate_acknowledgement",
]
