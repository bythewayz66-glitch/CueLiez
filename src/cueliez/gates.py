"""Hard gates for CueLiez high-stakes interview modes.

Consent, dual-control, prohibited-use enforcement, seal-time rules.
Language: observations and cues — never lie detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional
import time

SessionMode = Literal["interrogation", "therapy", "clinical", "government", "generic"]

CONSENT_REQUIRED_MODES = frozenset({"interrogation", "clinical", "government"})
DUAL_CONTROL_MODES = frozenset({"government"})

PROHIBITED_USES = (
    "automated_detention",
    "automated_charge",
    "automated_clearance",
    "definitive_deception_claim",
    "clinical_diagnosis",
    "medical_device_claim",
    "polygraph_substitute",
    "covert_surveillance_without_warrant",
    "employment_screening_without_notice",
    "immigration_adjudication",
    "child_custody_determination",
)

DISCLAIMER = (
    "All behavioural signals are probabilistic observations only. "
    "They do not constitute definitive proof of deception, emotion, or intent. "
    "CueLiez is not a lie detector, not a medical device, and not a polygraph. "
    "It must not be used for automated legal or clinical decisions."
)


@dataclass
class DualControlRecord:
    cue_id: str
    first_officer_id: str
    second_officer_id: str
    acknowledged_at: float
    notes: str = ""


@dataclass
class SessionGateState:
    mode: SessionMode
    consent: bool = False
    consent_recorded_at: Optional[float] = None
    consent_attested_by: Optional[str] = None
    operator_id: Optional[str] = None
    dual_control_records: List[DualControlRecord] = field(default_factory=list)
    intended_uses: List[str] = field(default_factory=list)
    training_acknowledged: bool = False
    training_version: Optional[str] = None

    def requires_consent(self) -> bool:
        return self.mode in CONSENT_REQUIRED_MODES

    def requires_dual_control(self) -> bool:
        return self.mode in DUAL_CONTROL_MODES

    def consent_ok(self) -> bool:
        if not self.requires_consent():
            return True
        return bool(self.consent and self.consent_recorded_at)


class GateError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def check_prohibited_uses(intended_uses: list[str] | None) -> None:
    if not intended_uses:
        return
    for use in intended_uses:
        key = use.strip().lower().replace(" ", "_")
        if key in PROHIBITED_USES:
            raise GateError("prohibited_use", f"Use '{use}' is prohibited by CueLiez policy.")


def require_consent(state: SessionGateState, *, action: str = "start") -> None:
    if state.requires_consent() and not state.consent_ok():
        raise GateError(
            "consent_required",
            f"Affirmative consent is required for mode={state.mode!r} before {action}.",
        )


def require_training(state: SessionGateState) -> None:
    if state.mode in CONSENT_REQUIRED_MODES and not state.training_acknowledged:
        raise GateError(
            "training_required",
            f"Operator training acknowledgement is required for mode={state.mode!r}.",
        )


def seal_observation_package(package: dict) -> dict:
    """Seal as observed indicators only — never findings."""
    if not isinstance(package, dict):
        raise GateError("seal_invalid", "Seal package must be a dict.")
    package["epistemic_status"] = "observed_indicator"
    package["origin"] = "grounded"
    package["is_definitive_finding"] = False
    package["disclaimer"] = DISCLAIMER
    package["product"] = "CueLiez"
    annotations = package.get("annotations") or {}
    banned = {"diagnosis", "legal_finding", "deception_confirmed", "guilty", "clearance_denied", "detain"}
    for k in annotations:
        if k.lower() in banned:
            raise GateError(
                "contamination_attempt",
                f"Annotation '{k}' would store a definitive claim. Observations only.",
            )
    return package
