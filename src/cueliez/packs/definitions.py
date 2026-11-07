"""Domain-specific cue pack definitions (gov, leg, med, thrp).

All packs produce observations/cues for human review only. They never produce
verdicts about deception or truthfulness, never diagnose, and never produce
legal/clinical findings. Consent, training, and dual-control requirements
remain enforced by gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..gates import DISCLAIMER, SessionGateState
from ..observations import ObservationRunner
from ..observations.behavioral import (
    AnswerLengthVarianceObserver,
    EvasionMarkerObserver,
    FilledPauseMarkerObserver,
    InterruptionOverlapObserver,
    ResponseLatencyObserver,
    SpeechRateShiftObserver,
)
from ..observations.consistency import (
    ClaimConflictObserver,
    DetailDriftObserver,
    LocationReferenceDivergenceObserver,
    SelfReferenceShiftObserver,
    TimelineInconsistencyObserver,
)
from ..observations.linguistic import (
    CertaintySwingObserver,
    DetailVaguenessObserver,
    HedgingObserver,
    MemoryQualifierObserver,
    MinimizationObserver,
    NegationDensityObserver,
    OverjustificationObserver,
    PassiveVoiceProxyObserver,
    PronounDistancingObserver,
)
from ..observations.physiological import ElectrodermalShiftObserver, HeartRateShiftObserver, HrvShiftObserver
from ..observations.prosody import PausePatternObserver, ProsodicVariabilityObserver, VoiceStressFeatureShiftObserver
from ..observations.visual import BlinkRateObserver, GazePatternObserver, MotorActivityObserver

# Compliant, non-verdict guidance fragments reused across packs.
_HUMAN_JUDGMENT = "Treat all outputs as probabilistic cues for human review; humans make all judgments."
_NO_VERDICTS = "Do not use outputs as findings of deception, intent, guilt, diagnosis, or clearance."


def _core_text_observers() -> list:
    return [
        HedgingObserver(),
        PronounDistancingObserver(),
        NegationDensityObserver(),
        DetailVaguenessObserver(),
        CertaintySwingObserver(),
        MinimizationObserver(),
        PassiveVoiceProxyObserver(),
        OverjustificationObserver(),
        MemoryQualifierObserver(),
        ClaimConflictObserver(),
        TimelineInconsistencyObserver(),
        DetailDriftObserver(),
        LocationReferenceDivergenceObserver(),
        SelfReferenceShiftObserver(),
        ResponseLatencyObserver(),
        AnswerLengthVarianceObserver(),
        EvasionMarkerObserver(),
        SpeechRateShiftObserver(),
        FilledPauseMarkerObserver(),
        InterruptionOverlapObserver(),
    ]


def _feature_observers() -> list:
    return [
        ProsodicVariabilityObserver(),
        PausePatternObserver(),
        VoiceStressFeatureShiftObserver(),
        GazePatternObserver(),
        BlinkRateObserver(),
        MotorActivityObserver(),
        HeartRateShiftObserver(),
        HrvShiftObserver(),
        ElectrodermalShiftObserver(),
    ]


@dataclass(frozen=True)
class CuePack:
    """A domain-specific bundle of observers and compliant operator guidance."""

    id: str
    name: str
    mode: str  # maps to gates.SessionGateState.mode
    description: str
    observer_factories: tuple = field(default_factory=tuple, repr=False)
    cue_guidance: tuple[str, ...] = field(default_factory=tuple)
    domain_notes: tuple[str, ...] = field(default_factory=tuple)
    disclaimer_addendum: str = ""
    include_feature_observers: bool = False

    def observers(self) -> List[Any]:
        obs = [f() if callable(f) and not hasattr(f, "observe") else f for f in self.observer_factories]
        # If factories stored class refs by accident, instantiate; prefer callables returning instances.
        out = []
        for o in obs:
            if isinstance(o, type):
                out.append(o())
            else:
                out.append(o)
        return out

    def runner(self, *, include_feature_observers: Optional[bool] = None) -> ObservationRunner:
        inc = self.include_feature_observers if include_feature_observers is None else include_feature_observers
        observers = self.observers()
        if inc:
            observers.extend(_feature_observers())
        return ObservationRunner(observers=observers)

    def make_gate_state(self, **kwargs: Any) -> SessionGateState:
        """Create a gate state for the pack's mode.

        This does NOT record consent/training/dual-control. Callers must satisfy
        all required gates before start/seal.
        """
        kwargs.setdefault("mode", self.mode)
        return SessionGateState(**kwargs)

    def build_package(
        self,
        transcript: Sequence[Mapping[str, Any]],
        *,
        session_id: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        include_convergence: bool = True,
        include_feature_observers: Optional[bool] = None,
    ) -> Dict[str, Any]:
        runner = self.runner(include_feature_observers=include_feature_observers)
        ann = dict(annotations or {})
        ann.setdefault("cue_pack", self.id)
        ann.setdefault("cue_pack_mode", self.mode)
        pkg = runner.build_package(transcript, session_id=session_id, annotations=ann, include_convergence=include_convergence)
        if self.disclaimer_addendum:
            pkg["domain_disclaimer_addendum"] = self.disclaimer_addendum
        pkg["cue_guidance"] = list(self.cue_guidance)
        return pkg

    def info(self) -> Dict[str, Any]:
        r = self.runner()
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "description": self.description,
            "observer_count": len(r.observers),
            "cue_guidance": list(self.cue_guidance),
            "domain_notes": list(self.domain_notes),
            "disclaimer": DISCLAIMER,
            "disclaimer_addendum": self.disclaimer_addendum,
            "gates": {
                "consent_required": self.mode in {"interrogation", "therapy", "clinical", "government"},
                "training_required": self.mode in {"interrogation", "therapy", "clinical", "government"},
                "dual_control_required": self.mode == "government",
            },
        }


def gov_pack() -> CuePack:
    return CuePack(
        id="gov",
        name="Government / High-Security Interview",
        mode="government",
        description=(
            "Cue pack for government/high-security interview contexts. Emphasizes "
            "consistency, timeline, and accountability cues with strict gate discipline."
        ),
        observer_factories=tuple(type(o) for o in _core_text_observers()),
        cue_guidance=(
            "Confirm identity, authority, jurisdiction, and scope before proceeding.",
            "Use cues to identify topics needing clarification; ask direct, non-leading follow-ups.",
            "Reconcile timeline, location, and numeric details against available records where lawful.",
            _HUMAN_JUDGMENT,
            _NO_VERDICTS,
            "Dual-control acknowledgement is required for high-priority cues before sealing in government mode.",
        ),
        domain_notes=(
            "Mode enforces consent, training, and dual-control gates.",
            "Feature-observer modalities require explicit lawful basis and consent where applicable.",
        ),
        include_feature_observers=False,
    )


def leg_pack() -> CuePack:
    return CuePack(
        id="leg",
        name="Legal Interview (Law Enforcement / Legal Process)",
        mode="interrogation",
        description=(
            "Cue pack for legal interviews in investigative or legal-process contexts. "
            "Focuses on testimony consistency, specificity, and response clarity."
        ),
        observer_factories=tuple(type(o) for o in _core_text_observers()),
        cue_guidance=(
            "Establish rapport and explain process as required by policy and law.",
            "When vagueness or hedging appears, request concrete who/what/when/where details.",
            "When possible statement conflicts appear, present each account neutrally and ask for reconciliation.",
            "Document observations and follow-up questions in the record; avoid conclusory labels.",
            _HUMAN_JUDGMENT,
            _NO_VERDICTS,
        ),
        domain_notes=(
            "Mode enforces consent and training gates.",
            "Not for automated detention, charging, clearance, or legal findings.",
        ),
        include_feature_observers=False,
    )


def med_pack() -> CuePack:
    return CuePack(
        id="med",
        name="Medical / Clinical Interview Support",
        mode="clinical",
        description=(
            "Cue pack for clinical interview support contexts (non-diagnostic). "
            "Focuses on clarity, consistency, and communication cues."
        ),
        observer_factories=tuple(type(o) for o in [
            HedgingObserver(), DetailVaguenessObserver(), CertaintySwingObserver(),
            MemoryQualifierObserver(), OverjustificationObserver(), MinimizationObserver(),
            ClaimConflictObserver(), TimelineInconsistencyObserver(), DetailDriftObserver(),
            ResponseLatencyObserver(), AnswerLengthVarianceObserver(), EvasionMarkerObserver(),
            FilledPauseMarkerObserver(), SpeechRateShiftObserver(),
        ]),
        cue_guidance=(
            "Use cues to support clear communication and careful history-taking.",
            "When memory qualifiers or vagueness appear, ask gentle clarifying questions and confirm understanding.",
            "Do not interpret communication patterns as diagnosis, symptom validity, or intent.",
            "Escalate clinical concerns through appropriate human clinical pathways, not automated outputs.",
            _HUMAN_JUDGMENT,
            "Not a medical device and not for clinical diagnosis or automated clinical decisions.",
        ),
        domain_notes=(
            "Mode enforces consent and training gates.",
            "Physiological/feature modalities, if used, must be consent-governed and clinically appropriate; outputs remain non-diagnostic cues.",
        ),
        disclaimer_addendum=(
            "Clinical/medical context addendum: observations support communication review only and "
            "must not be used for diagnosis, treatment decisions, or determinations of patient credibility."
        ),
        include_feature_observers=False,
    )


def thrp_pack() -> CuePack:
    return CuePack(
        id="thrp",
        name="Therapy / Supportive Interview",
        mode="therapy",
        description=(
            "Cue pack for therapy/supportive interview contexts. Prioritizes supportive "
            "clarification cues and avoids adversarial framing."
        ),
        observer_factories=tuple(type(o) for o in [
            HedgingObserver(), DetailVaguenessObserver(), CertaintySwingObserver(),
            MemoryQualifierObserver(), MinimizationObserver(), OverjustificationObserver(),
            ResponseLatencyObserver(), AnswerLengthVarianceObserver(), FilledPauseMarkerObserver(),
            SpeechRateShiftObserver(), SelfReferenceShiftObserver(),
        ]),
        cue_guidance=(
            "Use cues to notice moments that may benefit from clarification, pacing, or support.",
            "Prefer open, non-confrontational questions; avoid treating any cue as evidence of intent.",
            "When responses become brief or strained, consider safety, comfort, and pacing before probing.",
            "Do not use outputs for diagnosis, risk adjudication, or determinations of truthfulness.",
            _HUMAN_JUDGMENT,
            "Not a medical device and not for automated therapeutic or clinical decisions.",
        ),
        domain_notes=(
            "Mode enforces consent and training gates.",
            "Designed for supportive human-led contexts; never for coercive or covert use.",
        ),
        disclaimer_addendum=(
            "Therapy/support addendum: observations are communication/process cues only and "
            "must not be used to judge credibility, diagnose, or make automated care decisions."
        ),
        include_feature_observers=False,
    )


_PACKS: Dict[str, CuePack] = {}


def _register() -> None:
    for fn in (gov_pack, leg_pack, med_pack, thrp_pack):
        p = fn()
        _PACKS[p.id] = p


_register()


def get_pack(pack_id: str) -> CuePack:
    key = (pack_id or "").strip().lower()
    if key not in _PACKS:
        raise KeyError(f"Unknown cue pack {pack_id!r}. Available: {sorted(_PACKS)}")
    return _PACKS[key]


def list_packs() -> List[Dict[str, Any]]:
    return [p.info() for p in _PACKS.values()]
