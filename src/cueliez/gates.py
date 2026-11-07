"""Hard gates for CueLiez high-stakes interview modes.

Consent, dual-control, prohibited-use enforcement, seal-time rules.
Language: observations and cues — never lie detection.

Consent is tight: interrogation, clinical, government, and therapy all require
affirmative consent + non-empty attester before start and again before seal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional
import time

SessionMode = Literal["interrogation", "therapy", "clinical", "government", "generic"]

# All non-generic modes require recorded affirmative consent.
CONSENT_REQUIRED_MODES = frozenset({"interrogation", "therapy", "clinical", "government"})
DUAL_CONTROL_MODES = frozenset({"government"})
TRAINING_REQUIRED_MODES = frozenset({"interrogation", "therapy", "clinical", "government"})

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
    "lie_detector_claim",
)

DISCLAIMER = (
    "All behavioural signals are probabilistic observations only. "
    "They do not constitute definitive proof of deception, emotion, or intent. "
    "CueLiez is not a lie detector, not a medical device, and not a polygraph. "
    "It must not be used for automated legal or clinical decisions."
)

BANNED_ANNOTATION_KEYS = frozenset({
    "diagnosis",
    "legal_finding",
    "deception_confirmed",
    "lie_confirmed",
    "lying",
    "is_lying",
    "guilty",
    "not_guilty",
    "clearance_denied",
    "clearance_granted",
    "detain",
    "charge",
    "polygraph_result",
    "truth_score",
})


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
    subject_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    operator_id: Optional[str] = None
    dual_control_records: List[DualControlRecord] = field(default_factory=list)
    intended_uses: List[str] = field(default_factory=list)
    training_acknowledged: bool = False
    training_version: Optional[str] = None

    def requires_consent(self) -> bool:
        return self.mode in CONSENT_REQUIRED_MODES

    def requires_dual_control(self) -> bool:
        return self.mode in DUAL_CONTROL_MODES

    def requires_training(self) -> bool:
        return self.mode in TRAINING_REQUIRED_MODES

    def consent_ok(self) -> bool:
        if not self.requires_consent():
            return True
        attester = (self.consent_attested_by or "").strip()
        return bool(self.consent and self.consent_recorded_at and attester)


class GateError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

    def as_dict(self) -> dict:
        return {"ok": False, "error_code": self.code, "error": self.message}


def record_consent(
    state: SessionGateState,
    *,
    attested_by: str,
    subject_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
) -> None:
    """Record affirmative consent. Attester is mandatory."""
    who = (attested_by or "").strip()
    if not who:
        raise GateError(
            "consent_attester_required",
            "consent_attested_by must be a non-empty officer/clinician identifier.",
        )
    state.consent = True
    state.consent_recorded_at = time.time()
    state.consent_attested_by = who
    if subject_id is not None:
        state.subject_id = subject_id
    if jurisdiction is not None:
        state.jurisdiction = jurisdiction


def check_prohibited_uses(intended_uses: list[str] | None) -> None:
    if not intended_uses:
        return
    for use in intended_uses:
        key = use.strip().lower().replace(" ", "_")
        if key in PROHIBITED_USES:
            raise GateError("prohibited_use", f"Use '{use}' is prohibited by CueLiez policy.")


def require_consent(state: SessionGateState, *, action: str = "start") -> None:
    if not state.requires_consent():
        return
    if not state.consent_ok():
        raise GateError(
            "consent_required",
            f"Affirmative consent with non-empty consent_attested_by is required "
            f"for mode={state.mode!r} before {action}.",
        )


def require_training(state: SessionGateState) -> None:
    if not state.requires_training():
        return
    if not state.training_acknowledged:
        raise GateError(
            "training_required",
            f"Operator training acknowledgement is required for mode={state.mode!r}.",
        )
    if not (state.training_version or "").strip():
        raise GateError(
            "training_version_required",
            "training_version must be recorded when training is acknowledged.",
        )


def require_dual_control_for_seal(
    state: SessionGateState,
    high_priority_cue_ids: list[str],
) -> None:
    if not state.requires_dual_control():
        return
    if not high_priority_cue_ids:
        return
    acknowledged = {r.cue_id for r in state.dual_control_records}
    missing = [cid for cid in high_priority_cue_ids if cid not in acknowledged]
    if missing:
        raise GateError(
            "dual_control_incomplete",
            f"Government mode requires dual-control for high-priority cues before seal. Missing: {missing}.",
        )


def record_dual_acknowledge(
    state: SessionGateState,
    cue_id: str,
    first_officer_id: str,
    second_officer_id: str,
    notes: str = "",
) -> DualControlRecord:
    if not state.requires_dual_control():
        raise GateError(
            "dual_control_not_applicable",
            f"Dual control only applies to modes {sorted(DUAL_CONTROL_MODES)}.",
        )
    a = (first_officer_id or "").strip()
    b = (second_officer_id or "").strip()
    if not a or not b:
        raise GateError("dual_control_ids_required", "Both officer IDs are required.")
    if a == b:
        raise GateError("dual_control_same_officer", "Dual control requires two distinct IDs.")
    rec = DualControlRecord(
        cue_id=cue_id,
        first_officer_id=a,
        second_officer_id=b,
        acknowledged_at=time.time(),
        notes=notes or "",
    )
    state.dual_control_records.append(rec)
    return rec


def _validate_observation_entry(d: dict, index: int) -> None:
    conf = d.get("confidence")
    if not isinstance(conf, dict):
        raise GateError(
            "missing_confidence",
            f"Observation[{index}] must carry confidence object with score and model_id.",
        )
    if "score" not in conf:
        raise GateError("missing_confidence_score", f"Observation[{index}] missing confidence.score.")
    try:
        score = float(conf["score"])
    except (TypeError, ValueError):
        raise GateError("invalid_confidence_score", f"Observation[{index}] confidence.score must be numeric.")
    if score < 0.0 or score > 1.0:
        raise GateError("confidence_out_of_range", f"Observation[{index}] confidence.score must be in [0, 1].")
    if not (conf.get("model_id") or "").strip():
        raise GateError("missing_model_id", f"Observation[{index}] missing confidence.model_id.")
    # Reject verdict-shaped labels inside observations
    label = (d.get("label") or d.get("claim") or "").strip().lower()
    if label in {"lying", "lie", "deception_confirmed", "guilty", "truthful"}:
        raise GateError(
            "verdict_language",
            f"Observation[{index}] uses forbidden verdict label {label!r}. Indicators only.",
        )


def seal_observation_package(
    package: dict,
    state: Optional[SessionGateState] = None,
    *,
    high_priority_cue_ids: Optional[list[str]] = None,
) -> dict:
    """
    Harden and seal as observed indicators only — never findings.

    Re-checks consent, training, dual-control, and prohibited uses when state is provided.
    Forces epistemic fields; rejects banned annotations and incomplete observations.
    """
    if not isinstance(package, dict):
        raise GateError("seal_invalid", "Seal package must be a dict.")

    if state is not None:
        check_prohibited_uses(state.intended_uses)
        require_consent(state, action="seal")
        require_training(state)
        require_dual_control_for_seal(state, high_priority_cue_ids or [])

    # Refuse any attempt to mark the package as a definitive finding
    if package.get("is_definitive_finding") is True:
        raise GateError(
            "definitive_finding_forbidden",
            "Packages cannot be sealed with is_definitive_finding=true.",
        )
    if (package.get("epistemic_status") or "").lower() in {
        "fact_finding",
        "legal_finding",
        "diagnosis",
        "deception_confirmed",
    }:
        raise GateError(
            "epistemic_status_forbidden",
            "epistemic_status must remain an observation class, not a finding.",
        )

    package["epistemic_status"] = "observed_indicator"
    package["origin"] = "grounded"
    package["is_definitive_finding"] = False
    package["disclaimer"] = DISCLAIMER
    package["product"] = "CueLiez"
    package["sealed_at"] = time.time()

    annotations = package.get("annotations") or {}
    if not isinstance(annotations, dict):
        raise GateError("annotations_invalid", "annotations must be a dict.")
    for k in annotations:
        if k.lower() in BANNED_ANNOTATION_KEYS:
            raise GateError(
                "contamination_attempt",
                f"Annotation '{k}' would store a definitive claim. Observations only.",
            )

    observations = package.get("observations") or package.get("detections") or []
    if observations is None:
        observations = []
    if not isinstance(observations, list):
        raise GateError("observations_invalid", "observations must be a list.")
    for i, obs in enumerate(observations):
        if not isinstance(obs, dict):
            raise GateError("observation_invalid", f"Observation[{i}] must be a dict.")
        _validate_observation_entry(obs, i)

    # Prefer canonical key going forward
    package["observations"] = observations
    if "detections" in package:
        del package["detections"]

    package["firewall"] = {
        "contamination_check": "passed",
        "origin": "grounded",
        "epistemic_status": "observed_indicator",
        "is_definitive_finding": False,
        "consent_rechecked": state is not None and state.requires_consent(),
        "training_rechecked": state is not None and state.requires_training(),
    }
    return package
