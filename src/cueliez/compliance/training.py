"""Domain-specific training modules and gate integration.

Training content supports operator competency for cue-based, human-led use.
It is not legal, clinical, or investigative advice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid

from ..gates import GateError, SessionGateState

VERSION = "2026.1"


@dataclass
class TrainingModule:
    id: str
    title: str
    version: str
    domain: str
    mode: str
    objectives: List[str]
    required_topics: List[str]
    operator_responsibilities: List[str]
    prohibited_uses_review: List[str]
    assessment_checks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingAcknowledgement:
    module_id: str
    module_version: str
    operator_id: str
    attested_by: Optional[str] = None  # supervisor/trainer if applicable
    completed_topics: List[str] = field(default_factory=list)
    assessment_passed: bool = False
    acknowledged_at: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_COMMON_TOPICS = [
    "CueLiez purpose: observation and cue support for human-led interviews.",
    "Language rules: no lie-detector framing, no deception/truth/guilt findings, no diagnosis.",
    "How to read cues: probabilistic indicators, context dependence, false positives/negatives.",
    "Human judgment: operators ask follow-up questions and make decisions; system does not.",
    "Consent workflow: required disclosures, affirmative attestation, and mode-specific gates.",
    "Record handling: sealed packages store observed indicators with disclaimers, not verdicts.",
    "Prohibited uses and escalation: refuse automated or out-of-policy uses.",
]

_COMMON_PROHIBITED = [
    "No automated detention, charging, clearance, or legal findings.",
    "No definitive deception claims or conclusions that a person is being untruthful.",
    "No clinical diagnosis or medical-device use.",
    "No polygraph-substitute claims or covert/warrantless use outside lawful authority/policy.",
]


def _module(domain: str, mode: str, title: str, objectives: List[str], extra_topics: List[str],
            responsibilities: List[str], extra_prohibited: List[str], checks: List[str]) -> TrainingModule:
    return TrainingModule(
        id=f"cueliez-training-{domain}",
        title=title,
        version=VERSION,
        domain=domain,
        mode=mode,
        objectives=objectives,
        required_topics=_COMMON_TOPICS + extra_topics,
        operator_responsibilities=responsibilities,
        prohibited_uses_review=_COMMON_PROHIBITED + extra_prohibited,
        assessment_checks=checks,
    )


_MODULES: Dict[str, TrainingModule] = {
    "gov": _module(
        "gov", "government", "CueLiez Training — Government / High-Security",
        ["Operate CueLiez under government/high-security policy with strict gate discipline.",
         "Use cues to support clarification, not security findings."],
        ["Government mode gates: consent, training, and dual-control before sealing high-priority cues.",
         "Authority/jurisdiction/scope confirmation and records/classification handling per policy.",
         "Oversight, review, and escalation pathways."],
        ["Confirm lawful authority and scope before session start.",
         "Ensure consent/training are recorded; obtain dual-control acknowledgements where required.",
         "Document cues and follow-up actions neutrally; protect records per policy."],
        ["No automated clearance, access, or security determinations."],
        ["Can explain observation vs finding.", "Can identify when dual-control is required.", "Can refuse prohibited-use requests."],
    ),
    "leg": _module(
        "leg", "interrogation", "CueLiez Training — Legal / Investigative Interview",
        ["Conduct cue-assisted legal interviews with procedural fairness and accurate documentation.",
         "Use cues to guide questioning, not to reach legal conclusions."],
        ["Interview mode gates: consent and training requirements.",
         "Providing required notices/rights/warnings per applicable law and policy.",
         "Handling possible statement conflicts neutrally and documenting follow-up."],
        ["Follow jurisdiction/policy requirements for notices, rights, and recording.",
         "Record affirmative consent with a non-empty attester; complete required disclosures.",
         "Ask non-leading clarifying questions and avoid conclusory labels in documentation."],
        ["No automated detention, charging, or evidentiary conclusions from cues alone."],
        ["Can explain non-verdict language.", "Can document a cue and a neutral follow-up question.", "Can identify prohibited legal uses."],
    ),
    "med": _module(
        "med", "clinical", "CueLiez Training — Medical / Clinical Support (Non-Diagnostic)",
        ["Use CueLiez as communication/history-taking support in clinical contexts without diagnosis.",
         "Recognize and prevent medical-device/diagnostic misuse."],
        ["Clinical mode gates: consent and training requirements.",
         "Privacy/confidentiality and handling of health information per applicable law/policy.",
         "Optional feature modalities (audio/visual/physiological) as non-diagnostic, consent-governed summaries."],
        ["Use cues only to support clear communication and careful human-led history-taking.",
         "Do not interpret cues as diagnosis, symptom validity, or credibility.",
         "Escalate clinical concerns through qualified clinical pathways."],
        ["No diagnosis, treatment decisions, credibility determinations, or automated clinical decisions."],
        ["Can explain non-diagnostic limits.", "Can respond appropriately to a communication cue without labeling the patient.", "Can identify prohibited clinical uses."],
    ),
    "thrp": _module(
        "thrp", "therapy", "CueLiez Training — Therapy / Supportive Context",
        ["Use CueLiez to support pacing/clarification in a supportive, human-led context.",
         "Avoid adversarial or credibility-judging interpretations of cues."],
        ["Therapy mode gates: consent and training requirements.",
         "Supportive questioning, pacing, comfort/safety awareness, and boundaries.",
         "Privacy, ethics, and applicable legal/safety obligations."],
        ["Use cues as prompts for clarification/support, not evidence of intent or truthfulness.",
         "Prioritize safety, comfort, and professional judgment over cue-driven probing.",
         "Follow applicable ethical/legal/safety procedures and documentation practices."],
        ["No diagnosis, risk adjudication, credibility determinations, or automated care decisions."],
        ["Can reframe a cue into a supportive question.", "Can identify when to pause/probe less.", "Can identify prohibited therapeutic uses."],
    ),
}


def domain_training(domain: str, version: str = VERSION) -> TrainingModule:
    key = (domain or "").strip().lower()
    if key not in _MODULES:
        raise KeyError(f"Unknown training domain {domain!r}. Available: {sorted(_MODULES)}")
    m = _MODULES[key]
    return TrainingModule(**{**m.to_dict(), "version": version})


def get_training_bundle(domain: Optional[str] = None, *, version: str = VERSION) -> List[TrainingModule]:
    if domain and domain.strip().lower() not in ("", "all", "general"):
        return [domain_training(domain, version=version)]
    return [domain_training(d, version=version) for d in ("gov", "leg", "med", "thrp")]


def render_training_module(m: TrainingModule) -> str:
    lines = [f"# {m.title}", "", f"- **ID:** `{m.id}`", f"- **Version:** `{m.version}`", f"- **Domain:** `{m.domain}`", f"- **Mode:** `{m.mode}`", ""]
    def section(name: str, items: List[str]):
        lines.extend([f"## {name}"])
        for it in items:
            lines.append(f"- {it}")
        lines.append("")
    section("Objectives", m.objectives)
    section("Required topics", m.required_topics)
    section("Operator responsibilities", m.operator_responsibilities)
    section("Prohibited uses (review)", m.prohibited_uses_review)
    section("Assessment checks", m.assessment_checks)
    lines.extend(["## Acknowledgement", "- Operator ID: ____________________", "- Trainer/supervisor (if applicable): ____________________",
                  "- All required topics completed: [ ]", "- Assessment passed: [ ]", "- Training version: ____________________", "- Date/time: ____________________"])
    return "\n".join(lines) + "\n"


def validate_training_ack(module: TrainingModule, ack: TrainingAcknowledgement) -> Dict[str, Any]:
    notes = []
    if ack.module_id != module.id:
        notes.append("module_id_mismatch")
    if ack.module_version != module.version:
        notes.append("module_version_mismatch")
    if not (ack.operator_id or "").strip():
        notes.append("missing_operator_id")
    if not ack.assessment_passed:
        notes.append("assessment_not_passed")
    required = set(module.required_topics)
    done = set(ack.completed_topics or [])
    # if explicit completed list provided, check coverage; empty list means not evidenced
    if required and done and not required.issubset(done):
        missing = sorted(required - done)
        notes.append(f"missing_topics:{len(missing)}")
    elif required and not done:
        notes.append("completed_topics_not_recorded")
    return {
        "valid": len(notes) == 0,
        "notes": notes,
        "training_version": module.version,
        "operator_id": (ack.operator_id or "").strip(),
        "module_id": module.id,
    }


def apply_training_to_gate_state(module: TrainingModule, ack: TrainingAcknowledgement, state: SessionGateState, *, require_valid: bool = True) -> SessionGateState:
    result = validate_training_ack(module, ack)
    if require_valid and not result["valid"]:
        raise GateError("invalid_training_ack", f"Training acknowledgement is not valid: {result['notes']}")
    state.training_acknowledged = True
    state.training_version = module.version
    if result["operator_id"]:
        state.operator_id = state.operator_id or result["operator_id"]
    return state
