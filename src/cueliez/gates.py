"""Hard gates for CueLiez high-stakes interview modes.

Consent, dual-control, prohibited-use enforcement, seal-time rules.
Language: observations and cues — never lie detection.

Consent is tight: interrogation, clinical, government, and therapy all require
affirmative consent + non-empty attester before start and again before seal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional
import hashlib
import json
import time

try:
    from .audit import audit_event
except Exception:  # pragma: no cover
    def audit_event(*args: Any, **kwargs: Any) -> dict:  # type: ignore[no-redef]
        return {}

# Best-effort product version for sealed packages.
try:
    from . import __version__ as CUELIEZ_VERSION
except Exception:  # pragma: no cover
    CUELIEZ_VERSION = "0.0.0"

SEALED_PACKAGE_SCHEMA_VERSION = "1.0"

SessionMode = Literal["interrogation", "therapy", "clinical", "government", "generic"]

# All non-generic modes require recorded affirmative consent.
CONSENT_REQUIRED_MODES = frozenset({"interrogation", "therapy", "clinical", "government"})
DUAL_CONTROL_MODES = frozenset({"government"})
TRAINING_REQUIRED_MODES = frozenset({"interrogation", "therapy", "clinical", "government"})

# Gated input modalities (feature extraction / sensors). Off by default; require
# explicit modality consent + jurisdiction validation before enabling.
GATED_INPUT_MODALITIES = frozenset({"audio_features", "camera", "wearable"})

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

# Canonical disclaimer version (hash-based: changes if disclaimer text changes).
DISCLAIMER_VERSION = "v1-" + hashlib.sha256(DISCLAIMER.encode("utf-8")).hexdigest()[:12]

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

FORBIDDEN_OBSERVATION_LABELS = frozenset({
    "lying", "lie", "deception_confirmed", "guilty", "truthful",
    "deceptive", "dishonest", "honest",
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
    # Gated input modalities (audio_features, camera, wearable): explicit consent + jurisdiction.
    modality_consents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    jurisdiction_approved: bool = False

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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full gate state for sealed packages (self-describing)."""
        return {
            "mode": self.mode,
            "consent": bool(self.consent),
            "consent_recorded_at": self.consent_recorded_at,
            "consent_attested_by": self.consent_attested_by,
            "subject_id": self.subject_id,
            "jurisdiction": self.jurisdiction,
            "operator_id": self.operator_id,
            "dual_control_records": [asdict(r) for r in (self.dual_control_records or [])],
            "intended_uses": list(self.intended_uses or []),
            "training_acknowledged": bool(self.training_acknowledged),
            "training_version": self.training_version,
            "modality_consents": dict(self.modality_consents or {}),
            "jurisdiction_approved": bool(self.jurisdiction_approved),
            "requirements": {
                "consent_required": self.requires_consent(),
                "training_required": self.requires_training(),
                "dual_control_required": self.requires_dual_control(),
            },
        }


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


def record_modality_consent(
    state: SessionGateState,
    modality: str,
    *,
    attested_by: str,
    jurisdiction: Optional[str] = None,
    jurisdiction_approved: bool = True,
) -> None:
    """Record explicit consent + jurisdiction approval for a gated input modality."""
    key = (modality or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key not in GATED_INPUT_MODALITIES:
        raise GateError(
            "unsupported_gated_modality",
            f"Modality {modality!r} is not a supported gated input modality: {sorted(GATED_INPUT_MODALITIES)}.",
        )
    who = (attested_by or "").strip()
    if not who:
        raise GateError(
            "consent_attester_required",
            "attested_by must be a non-empty identifier for modality consent.",
        )
    if jurisdiction is not None:
        state.jurisdiction = (jurisdiction or "").strip() or state.jurisdiction
    state.modality_consents[key] = {
        "consented": True,
        "attested_by": who,
        "jurisdiction": state.jurisdiction,
        "jurisdiction_approved": bool(jurisdiction_approved),
        "recorded_at": time.time(),
    }
    if jurisdiction_approved and (state.jurisdiction or "").strip():
        state.jurisdiction_approved = True


def require_gated_modality(state: SessionGateState, modality: str) -> None:
    """Fail closed: explicit consent + jurisdiction validation before enabling gated input."""
    if state is None:
        raise GateError("gate_state_required", "Session gate state is required for modality checks.")
    key = (modality or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key not in GATED_INPUT_MODALITIES:
        return
    rec = (state.modality_consents or {}).get(key)
    if not rec or not rec.get("consented"):
        raise GateError(
            "modality_consent_required",
            f"Explicit consent is required before enabling gated input modality {key!r}.",
        )
    att = (rec.get("attested_by") or state.consent_attested_by or "").strip()
    if not att:
        raise GateError(
            "consent_attester_required",
            f"Non-empty attester is required for gated input modality {key!r}.",
        )
    jur = (rec.get("jurisdiction") or state.jurisdiction or "").strip()
    if not jur:
        raise GateError(
            "jurisdiction_required",
            f"Jurisdiction must be recorded before enabling gated input modality {key!r}.",
        )
    approved = bool(rec.get("jurisdiction_approved")) or bool(state.jurisdiction_approved)
    if not approved:
        raise GateError(
            "jurisdiction_approval_required",
            f"Jurisdiction approval is required before enabling gated input modality {key!r}.",
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
    label = (d.get("label") or d.get("claim") or "").strip()
    if not label:
        raise GateError("missing_label", f"Observation[{index}] must carry a neutral label.")
    if label.strip().lower() in FORBIDDEN_OBSERVATION_LABELS:
        raise GateError(
            "verdict_language",
            f"Observation[{index}] uses forbidden verdict label {label!r}. Indicators only.",
        )
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
    if not (str(d.get("method") or "").strip()):
        raise GateError("missing_method", f"Observation[{index}] missing method.")
    if not (str(d.get("category") or "").strip()):
        raise GateError("missing_category", f"Observation[{index}] missing category.")


def _canonical_json_for_hash(package: Dict[str, Any]) -> str:
    """Stable canonical form for hashing. Excludes volatile/hash/signature fields."""
    excluded = {"package_hash", "content_hash", "sealed_at", "package_signature"}
    canonical = {k: v for k, v in package.items() if k not in excluded}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def compute_package_hash(package: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_for_hash(package).encode("utf-8")).hexdigest()


def verify_package_hash(package: Any) -> bool:
    """Return True if package_hash matches canonical content (offline verification)."""
    if not isinstance(package, dict):
        return False
    expected = str(package.get("package_hash") or "").strip()
    if not expected:
        return False
    return compute_package_hash(package) == expected


def package_completeness(package: Any) -> Dict[str, Any]:
    """Report sealed-package completeness/integrity checks (observations only; no findings)."""
    if not isinstance(package, dict):
        return {"ok": False, "errors": ["not_a_dict"]}
    errors = []
    for k in ("schema_version", "product", "product_version", "epistemic_status", "origin",
              "disclaimer", "disclaimer_version", "gate_state", "observations", "package_hash", "sealed_at"):
        if k not in package or package.get(k) in (None, ""):
            if k != "observations":  # observations can be empty list
                errors.append(f"missing:{k}")
    if "observations" not in package or not isinstance(package.get("observations"), list):
        if "missing:observations" not in errors:
            errors.append("invalid:observations")
    if package.get("epistemic_status") != "observed_indicator":
        errors.append("invalid:epistemic_status")
    if package.get("is_definitive_finding") is not False:
        errors.append("invalid:is_definitive_finding")
    if package.get("origin") != "grounded":
        errors.append("invalid:origin")
    if not verify_package_hash(package):
        errors.append("invalid:package_hash")
    gs = package.get("gate_state")
    if not isinstance(gs, dict):
        errors.append("invalid:gate_state")
    return {"ok": len(errors) == 0, "errors": errors}


def validate_sealed_package_ingest(package: Any) -> Dict[str, Any]:
    """Validate a sealed package for connector/ingest (original artifact). Fail-closed.

    Returns a minimal receipt on success. Raises GateError with auditable codes on failure.
    """
    if not isinstance(package, dict):
        raise GateError("ingest_invalid_package", "Ingest requires a package dict.")
    if not package.get("sealed"):
        raise GateError("ingest_not_sealed", "Ingest requires a sealed package (sealed=true).")
    rep = package_completeness(package)
    if not rep.get("ok"):
        errs = rep.get("errors") or []
        if "invalid:package_hash" in errs or any("missing:package_hash" in str(e) for e in errs):
            raise GateError("ingest_hash_mismatch", f"Package integrity verification failed: {errs}")
        if "invalid:epistemic_status" in errs or "invalid:is_definitive_finding" in errs:
            raise GateError("ingest_epistemic_invalid", f"Package epistemic/disclaimer fields invalid: {errs}")
        raise GateError("connector_validation_failed", f"Package validation failed: {errs}")
    if not verify_package_hash(package):
        raise GateError("ingest_hash_mismatch", "Package hash verification failed.")
    return {
        "ok": True,
        "package_hash": package.get("package_hash"),
        "schema_version": package.get("schema_version"),
        "epistemic_status": package.get("epistemic_status"),
        "sealed_at": package.get("sealed_at"),
        "mode": (package.get("gate_state") or {}).get("mode") if isinstance(package.get("gate_state"), dict) else None,
    }


def custody_receipt(package: Any) -> Dict[str, Any]:
    """Minimal custody receipt (safe to share for process review; no findings)."""
    if not isinstance(package, dict):
        return {}
    gs = package.get("gate_state") if isinstance(package.get("gate_state"), dict) else {}
    return {
        "product": package.get("product"),
        "product_version": package.get("product_version"),
        "schema_version": package.get("schema_version"),
        "package_hash": package.get("package_hash"),
        "sealed_at": package.get("sealed_at"),
        "epistemic_status": package.get("epistemic_status"),
        "is_definitive_finding": package.get("is_definitive_finding"),
        "disclaimer_version": package.get("disclaimer_version"),
        "mode": gs.get("mode"),
        "consent_attester_present": bool((gs.get("consent_attested_by") or "").strip()),
        "training_acknowledged": bool(gs.get("training_acknowledged")),
        "dual_control_record_count": len(gs.get("dual_control_records") or []) if isinstance(gs.get("dual_control_records"), list) else 0,
    }


def sign_package(package: Dict[str, Any], signer: Any = None) -> Dict[str, Any]:
    """Optional pluggable signing hook. Default is a no-op (never breaks seal).

    If `signer` is callable, it is invoked as `signer(package_hash=..., package=...)`
    or `signer(package)` and its return value is stored in `package_signature`.
    The signature is excluded from `package_hash` canonicalization.
    Mutates and returns `package` when it is a dict.
    """
    if not isinstance(package, dict):
        return package
    if signer is None:
        package.setdefault("package_signature", None)
        return package
    try:
        if callable(signer):
            try:
                sig = signer(package_hash=package.get("package_hash"), package=package)
            except TypeError:
                sig = signer(package)
            package["package_signature"] = sig
        else:
            package["package_signature"] = {"type": "unconfigured", "detail": "signer not callable"}
    except Exception as e:
        package["package_signature"] = {"type": "error", "error": str(e)}
    return package


def is_sealed(package: Any) -> bool:
    if not isinstance(package, dict):
        return False
    return package.get("sealed") is True or (
        package.get("package_hash") and package.get("sealed_at") and package.get("epistemic_status") == "observed_indicator"
    )


def assert_not_sealed(package: Any, *, action: str = "modify") -> None:
    if is_sealed(package):
        raise GateError(
            "package_sealed",
            f"Cannot {action} a sealed package. Officer notes and package changes must occur before seal.",
        )


HIGH_PRIORITY_LEVELS = frozenset({"high", "critical"})


def extract_high_priority_cue_ids(package: Any) -> List[str]:
    """Extract cue IDs that require dual-control review in government mode.

    Contract (documented for glyph/kilo/CLI):
    - `high_priority_cue_ids` may be supplied explicitly to `seal_observation_package`/session seal.
    - If not supplied, ids are extracted from package `cues` and/or `observations` entries where
      `priority` is `high` or `critical` (case-insensitive) and a `cue_id`/`id` is present.
    - Government mode fails closed when dual-control records are missing for extracted/provided ids.
    """
    if not isinstance(package, dict):
        return []
    ids: List[str] = []
    seen = set()
    for collection_key in ("cues", "observations"):
        items = package.get(collection_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            priority = str(item.get("priority") or "").strip().lower()
            if priority not in HIGH_PRIORITY_LEVELS:
                continue
            cid = item.get("cue_id") or item.get("id")
            if cid is None:
                continue
            cid_s = str(cid).strip()
            if not cid_s or cid_s in seen:
                continue
            seen.add(cid_s)
            ids.append(cid_s)
    return ids


def seal_observation_package(
    package: dict,
    state: Optional[SessionGateState] = None,
    *,
    high_priority_cue_ids: Optional[list[str]] = None,
    signer: Any = None,
) -> dict:
    """
    Harden and seal as observed indicators only — never findings.

    Re-checks consent, training, dual-control, and prohibited uses when state is provided.
    Forces epistemic fields; rejects banned annotations and incomplete observations.
    Serializes full gate state into the package and computes a stable SHA-256 content hash.

    For observation-only sealing without a session context, callers may omit state; a
    generic (no-gate) state is recorded. High-stakes mode enforcement is fail-closed
    whenever a high-stakes SessionGateState is supplied.
    """
    if not isinstance(package, dict):
        raise GateError("seal_invalid", "Seal package must be a dict.")
    if is_sealed(package):
        raise GateError("package_sealed", "Package is already sealed; post-seal mutation/re-seal is not allowed.")

    effective_state = state if state is not None else SessionGateState(mode="generic")

    if state is not None:
        check_prohibited_uses(state.intended_uses)
        require_consent(state, action="seal")
        require_training(state)
        resolved_high_priority = (
            list(high_priority_cue_ids)
            if high_priority_cue_ids is not None
            else extract_high_priority_cue_ids(package)
        )
        require_dual_control_for_seal(state, resolved_high_priority)

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

    package["schema_version"] = SEALED_PACKAGE_SCHEMA_VERSION
    package["epistemic_status"] = "observed_indicator"
    package["origin"] = "grounded"
    package["is_definitive_finding"] = False
    package["disclaimer"] = DISCLAIMER
    package["disclaimer_version"] = DISCLAIMER_VERSION
    package["product"] = "CueLiez"
    package["product_version"] = CUELIEZ_VERSION
    package["gate_state"] = effective_state.to_dict()

    if "annotations" in package and package["annotations"] is not None and not isinstance(package["annotations"], dict):
        raise GateError("annotations_invalid", "annotations must be a dict.")
    annotations = package.get("annotations") or {}
    if not isinstance(annotations, dict):
        annotations = {}
    for k in annotations:
        if k.lower() in BANNED_ANNOTATION_KEYS:
            raise GateError(
                "contamination_attempt",
                f"Annotation '{k}' would store a definitive claim. Observations only.",
            )

    if "observations" in package and package["observations"] is not None and not isinstance(package["observations"], list):
        raise GateError("observations_invalid", "observations must be a list.")
    if "observations" not in package and "detections" in package and package["detections"] is not None and not isinstance(package["detections"], list):
        raise GateError("observations_invalid", "observations must be a list.")
    observations = package.get("observations") if "observations" in package else package.get("detections")
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

    package["sealed"] = True
    package["firewall"] = {
        "contamination_check": "passed",
        "origin": "grounded",
        "epistemic_status": "observed_indicator",
        "is_definitive_finding": False,
        "consent_rechecked": state is not None and state.requires_consent(),
        "training_rechecked": state is not None and state.requires_training(),
        "gate_state_captured": True,
    }

    # Stable content hash over canonical package content (excludes sealed_at/package_hash).
    package.pop("package_hash", None)
    package.pop("content_hash", None)
    package.setdefault("package_signature", None)
    package["package_hash"] = compute_package_hash(package)
    package["sealed_at"] = time.time()
    if signer is not None:
        package = sign_package(package, signer=signer)
    elif package.get("package_signature") is None:
        package["package_signature"] = None
    try:
        audit_event("gate.seal", details={"mode": effective_state.mode, "observation_count": len(observations), "has_signature": bool(package.get("package_signature")), "schema_version": package.get("schema_version")})
    except Exception:
        pass
    return package


def export_sealed_package_json(package: Dict[str, Any], *, indent: int = 2) -> str:
    """Export a sealed package as structured JSON for disclosure/review.

    The export makes observations and active gate state understandable without
    claiming the system decided anything.
    """
    if not isinstance(package, dict):
        raise GateError("export_invalid", "Package must be a dict.")
    if package.get("epistemic_status") != "observed_indicator":
        raise GateError("export_invalid", "Only sealed observed-indicator packages may be exported.")
    return json.dumps(package, indent=indent, ensure_ascii=False, sort_keys=False, default=str)
