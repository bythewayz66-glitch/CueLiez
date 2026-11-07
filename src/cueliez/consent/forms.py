"""Consent forms and consent-system integration.

Operational consent templates and records for CueLiez. These templates support
workflow compliance and must be reviewed/adapted for applicable law, policy,
and jurisdiction by qualified humans. They do not constitute legal advice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence
import time
import uuid

from ..gates import DISCLAIMER, GateError, SessionGateState, record_consent

FORM_VERSION = "2026.1"


@dataclass
class ConsentDisclosure:
    id: str
    title: str
    text: str
    required: bool = True
    domain: str = "general"


@dataclass
class ConsentForm:
    id: str
    title: str
    version: str
    domain: str  # general|gov|leg|med|thrp
    mode: Optional[str]  # gates mode or None for general
    purpose: str
    disclosures: List[ConsentDisclosure] = field(default_factory=list)
    subject_fields: List[str] = field(default_factory=list)
    attester_fields: List[str] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)

    def disclosure_map(self) -> Dict[str, ConsentDisclosure]:
        return {d.id: d for d in self.disclosures}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsentAcknowledgement:
    """Affirmative acknowledgement captured by the operator workflow."""

    form_id: str
    form_version: str
    attested_by: str
    subject_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    acknowledged_disclosure_ids: List[str] = field(default_factory=list)
    subject_name_or_ref: Optional[str] = None
    subject_statement: str = ""  # e.g., recorded verbal/written affirmation summary
    questions_opportunity_confirmed: bool = False
    voluntariness_confirmed: bool = False
    session_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    acknowledged_at: Optional[float] = None


@dataclass
class ConsentRecord:
    record_id: str
    form_id: str
    form_version: str
    domain: str
    mode: Optional[str]
    attested_by: str
    subject_id: Optional[str]
    jurisdiction: Optional[str]
    acknowledged_disclosure_ids: List[str]
    questions_opportunity_confirmed: bool
    voluntariness_confirmed: bool
    subject_statement: str
    recorded_at: float
    valid: bool
    validation_notes: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_GENERAL_DISCLOSURES = [
    ConsentDisclosure(
        "g_purpose",
        "Purpose",
        "CueLiez is used to support a human-led interview by observing behavioural/linguistic "
        "signals and testimony consistency patterns and presenting them as cues for professional review.",
    ),
    ConsentDisclosure(
        "g_not_detector",
        "Not a lie detector / no verdicts",
        "CueLiez is not a lie detector, not a polygraph, and not a truth machine. It does not "
        "determine whether anyone is lying, truthful, guilty, or innocent. Outputs are probabilistic "
        "observations/cues for human judgment, not findings.",
    ),
    ConsentDisclosure(
        "g_no_automated_decisions",
        "No automated decisions",
        "CueLiez outputs must not be used as the sole or automated basis for detention, charging, "
        "clearance, diagnosis, treatment decisions, employment/immigration/custody determinations, "
        "or other legal/clinical decisions.",
    ),
    ConsentDisclosure(
        "g_data_recording",
        "Session data and records",
        "Session information, observations, and operator notes may be recorded, stored, and reviewed "
        "as permitted by applicable law, policy, and the purpose of the session. Sealed records "
        "preserve observed indicators with context and disclaimers, not verdicts.",
    ),
    ConsentDisclosure(
        "g_human_review",
        "Human review and questions",
        "A qualified human professional is responsible for interpreting cues, asking questions, and "
        "making decisions. You may ask questions about the process as permitted by applicable law/policy.",
    ),
    ConsentDisclosure(
        "g_rights_voluntariness",
        "Rights and voluntariness (jurisdiction/policy dependent)",
        "Any rights, voluntariness, refusal, withdrawal, counsel/access, and consequence information "
        "depends on the session type, jurisdiction, and applicable law/policy. The operator must provide "
        "required notices and follow applicable procedures before relying on this consent.",
    ),
]


def general_consent_form(version: str = FORM_VERSION) -> ConsentForm:
    return ConsentForm(
        id="cueliez-consent-general",
        title="CueLiez General Consent and Disclosure",
        version=version,
        domain="general",
        mode=None,
        purpose="General informed disclosure for CueLiez-assisted interview support.",
        disclosures=list(_GENERAL_DISCLOSURES),
        subject_fields=["subject_name_or_ref", "subject_id (if applicable)", "date/time", "session/location (as applicable)"],
        attester_fields=["attested_by (operator/professional ID)", "role", "jurisdiction/policy reference", "date/time"],
        notices=[
            DISCLAIMER,
            "Template notice: review/adapt for applicable law, policy, and jurisdiction before use.",
        ],
    )


_DOMAIN_SUPPLEMENTS: Dict[str, ConsentForm] = {
    "gov": ConsentForm(
        id="cueliez-consent-gov-supp",
        title="CueLiez Supplementary Consent/Disclosure — Government / High-Security",
        version=FORM_VERSION,
        domain="gov",
        mode="government",
        purpose="Supplementary disclosure for government/high-security interview contexts.",
        disclosures=[
            ConsentDisclosure("gov_authority", "Authority, jurisdiction, and scope",
                "The operator must identify the lawful authority, jurisdiction, scope, and applicable "
                "policy for the session. CueLiez does not determine authority or legality."),
            ConsentDisclosure("gov_dual_control", "Dual-control and oversight",
                "Government-mode sessions may require dual-control acknowledgement for high-priority cues "
                "before sealing records. Oversight and review follow applicable policy."),
            ConsentDisclosure("gov_records", "Records handling",
                "Records are handled according to applicable government policy, classification, retention, "
                "and disclosure rules. This form does not override those rules."),
            ConsentDisclosure("gov_no_clearance", "No automated security findings",
                "CueLiez outputs must not be used for automated clearance, access, detention, or security findings."),
        ],
        notices=["High-stakes mode: consent, training, and dual-control gates are enforced by the system where required."],
    ),
    "leg": ConsentForm(
        id="cueliez-consent-leg-supp",
        title="CueLiez Supplementary Consent/Disclosure — Legal / Investigative Interview",
        version=FORM_VERSION,
        domain="leg",
        mode="interrogation",
        purpose="Supplementary disclosure for legal/investigative interview contexts.",
        disclosures=[
            ConsentDisclosure("leg_context", "Legal/investigative context",
                "The operator must explain the nature of the interview and provide all notices required by "
                "applicable law, policy, and jurisdiction."),
            ConsentDisclosure("leg_rights", "Rights and required notices",
                "Rights, counsel/access, warnings, voluntariness, and recording notices are governed by "
                "applicable law/policy and must be completed by the operator. This template does not provide legal advice."),
            ConsentDisclosure("leg_no_legal_finding", "No legal findings",
                "CueLiez outputs are not legal findings, evidence of guilt/innocence, or determinations of deception. "
                "They may only be used as cues to guide human questioning and documentation."),
            ConsentDisclosure("leg_records", "Documentation and review",
                "Observations, cues, and follow-up actions should be documented according to policy. Sealed "
                "packages preserve observed indicators and disclaimers, not verdicts."),
        ],
        notices=["High-stakes mode: consent and training gates are enforced by the system."],
    ),
    "med": ConsentForm(
        id="cueliez-consent-med-supp",
        title="CueLiez Supplementary Consent/Disclosure — Medical / Clinical Support",
        version=FORM_VERSION,
        domain="med",
        mode="clinical",
        purpose="Supplementary disclosure for clinical interview support (non-diagnostic).",
        disclosures=[
            ConsentDisclosure("med_not_device", "Not a medical device / not diagnostic",
                "CueLiez is not a medical device and does not provide diagnosis, treatment recommendations, "
                "or clinical determinations. It does not assess symptom validity or patient credibility."),
            ConsentDisclosure("med_support", "Communication support only",
                "Any cues are intended to support clear communication and careful human-led history-taking. "
                "Clinical concerns must be addressed through qualified clinical judgment and applicable pathways."),
            ConsentDisclosure("med_privacy", "Privacy and health information",
                "Health/session information must be handled according to applicable privacy laws, policies, "
                "and professional obligations (for example, consent, confidentiality, and record rules as applicable)."),
            ConsentDisclosure("med_modalities", "Optional feature modalities",
                "If audio/prosody, visual, or physiological feature summaries are used, they must be "
                "lawfully obtained, consent-governed, and interpreted as non-diagnostic observations only."),
        ],
        notices=["Clinical mode: consent and training gates are enforced by the system."],
    ),
    "thrp": ConsentForm(
        id="cueliez-consent-thrp-supp",
        title="CueLiez Supplementary Consent/Disclosure — Therapy / Supportive Context",
        version=FORM_VERSION,
        domain="thrp",
        mode="therapy",
        purpose="Supplementary disclosure for therapy/supportive interview contexts.",
        disclosures=[
            ConsentDisclosure("thrp_supportive", "Supportive, non-adversarial use",
                "CueLiez cues may be used to notice moments for clarification, pacing, or support in a "
                "human-led therapeutic/supportive context. Cues are not evidence of intent or credibility."),
            ConsentDisclosure("thrp_not_clinical_finding", "No diagnosis or credibility findings",
                "CueLiez is not a medical device and does not diagnose, adjudicate risk, determine truthfulness, "
                "or make automated care decisions."),
            ConsentDisclosure("thrp_boundaries", "Boundaries, safety, and privacy",
                "The professional must follow applicable ethical, legal, privacy, and safety obligations. "
                "Use of CueLiez does not replace professional judgment or required procedures."),
            ConsentDisclosure("thrp_voluntary", "Participation and comfort",
                "As permitted by context and policy, the subject may ask questions, request pauses, or discuss "
                "comfort with the process. The operator must follow applicable consent and care procedures."),
        ],
        notices=["Therapy mode: consent and training gates are enforced by the system."],
    ),
}


def domain_supplement(domain: str, version: str = FORM_VERSION) -> ConsentForm:
    key = (domain or "").strip().lower()
    if key not in _DOMAIN_SUPPLEMENTS:
        raise KeyError(f"Unknown consent domain {domain!r}. Available: {sorted(_DOMAIN_SUPPLEMENTS)}")
    base = _DOMAIN_SUPPLEMENTS[key]
    # preserve requested version
    return ConsentForm(**{**base.to_dict(), "version": version, "disclosures": [ConsentDisclosure(**asdict(d)) for d in base.disclosures]})


def get_consent_bundle(domain: Optional[str] = None, *, version: str = FORM_VERSION) -> List[ConsentForm]:
    forms = [general_consent_form(version=version)]
    if domain and domain.strip().lower() not in ("", "general"):
        forms.append(domain_supplement(domain, version=version))
    return forms


def render_consent_form(form: ConsentForm) -> str:
    lines = [
        f"# {form.title}",
        "",
        f"- **Form ID:** `{form.id}`",
        f"- **Version:** `{form.version}`",
        f"- **Domain:** `{form.domain}`",
        f"- **Mode:** `{form.mode or 'general'}`",
        "",
        "## Purpose",
        form.purpose,
        "",
        "## Disclosures",
    ]
    for i, d in enumerate(form.disclosures, 1):
        req = "required" if d.required else "optional"
        lines.append(f"{i}. **{d.title}** ({req}, `{d.id}`)")
        lines.append(f"   - {d.text}")
    lines.extend(["", "## Subject/session fields (complete as applicable)"])
    for f in form.subject_fields or ["subject reference", "date/time"]:
        lines.append(f"- {f}")
    lines.extend(["", "## Attester/professional fields"])
    for f in form.attester_fields or ["attested_by", "role", "date/time"]:
        lines.append(f"- {f}")
    if form.notices:
        lines.extend(["", "## Notices"])
        for n in form.notices:
            lines.append(f"- {n}")
    lines.extend([
        "",
        "## Acknowledgement record (workflow capture)",
        "- All required disclosures reviewed/provided as applicable: [ ]",
        "- Opportunity for questions provided as applicable: [ ]",
        "- Voluntariness/required notices handled per law/policy: [ ]",
        "- Subject affirmation/statement summary: ____________________",
        "- Attested by (non-empty): ____________________",
        "- Date/time: ____________________",
    ])
    return "\n".join(lines) + "\n"


def validate_acknowledgement(form: ConsentForm, ack: ConsentAcknowledgement) -> ConsentRecord:
    notes: List[str] = []
    required_ids = {d.id for d in form.disclosures if d.required}
    ack_ids = set(ack.acknowledged_disclosure_ids or [])
    missing = sorted(required_ids - ack_ids)
    if missing:
        notes.append(f"missing_required_disclosures:{','.join(missing)}")
    if not (ack.attested_by or "").strip():
        notes.append("missing_attested_by")
    if not ack.questions_opportunity_confirmed:
        notes.append("questions_opportunity_not_confirmed")
    if not ack.voluntariness_confirmed:
        notes.append("voluntariness_not_confirmed")
    if ack.form_id != form.id:
        notes.append("form_id_mismatch")
    if ack.form_version != form.version:
        notes.append("form_version_mismatch")
    valid = len(notes) == 0
    ts = ack.acknowledged_at if ack.acknowledged_at is not None else time.time()
    return ConsentRecord(
        record_id=str(uuid.uuid4()),
        form_id=form.id,
        form_version=form.version,
        domain=form.domain,
        mode=form.mode,
        attested_by=(ack.attested_by or "").strip(),
        subject_id=ack.subject_id,
        jurisdiction=ack.jurisdiction,
        acknowledged_disclosure_ids=sorted(ack_ids),
        questions_opportunity_confirmed=ack.questions_opportunity_confirmed,
        voluntariness_confirmed=ack.voluntariness_confirmed,
        subject_statement=ack.subject_statement or "",
        recorded_at=ts,
        valid=valid,
        validation_notes=notes,
        session_id=ack.session_id,
        extra=dict(ack.extra or {}),
    )


def apply_consent_to_gate_state(
    record: ConsentRecord,
    state: SessionGateState,
    *,
    require_valid: bool = True,
) -> SessionGateState:
    """Apply a consent record to a gate state.

    This records affirmative consent in the gate only when the consent workflow
    record is valid (or require_valid=False) and an attester is present.
    It does not bypass gates; gates still enforce consent before start/seal.
    """
    if require_valid and not record.valid:
        raise GateError("invalid_consent_record", f"Consent record is not valid: {record.validation_notes}")
    record_consent(
        state,
        attested_by=record.attested_by,
        subject_id=record.subject_id,
        jurisdiction=record.jurisdiction,
    )
    return state
