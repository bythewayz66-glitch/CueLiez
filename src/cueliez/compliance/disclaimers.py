"""General and domain-specific disclaimers for CueLiez.

Disclaimers reinforce observation/cue-only use. They are operational text and
not legal or clinical advice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from ..gates import DISCLAIMER as BASE_DISCLAIMER

VERSION = "2026.1"


@dataclass
class Disclaimer:
    id: str
    title: str
    version: str
    domain: str
    body: str
    bullets: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def general_disclaimer(version: str = VERSION) -> Disclaimer:
    return Disclaimer(
        id="cueliez-disclaimer-general",
        title="CueLiez General Disclaimer",
        version=version,
        domain="general",
        body=BASE_DISCLAIMER,
        bullets=[
            "CueLiez provides observation and cue support for human-led interviews only.",
            "Outputs are probabilistic indicators; they may be incomplete, context-dependent, or wrong.",
            "Humans are responsible for interpretation, follow-up questions, decisions, and documentation.",
            "Do not use outputs for automated legal, security, employment, immigration, custody, or clinical decisions.",
            "Do not describe or use CueLiez as a lie detector, polygraph, or truth machine.",
        ],
    )


_DOMAIN: Dict[str, Disclaimer] = {
    "gov": Disclaimer(
        id="cueliez-disclaimer-gov",
        title="CueLiez Disclaimer — Government / High-Security Context",
        version=VERSION,
        domain="gov",
        body="Government/high-security use remains subject to the general disclaimer and all applicable authority, policy, classification, and oversight rules.",
        bullets=[
            "Not for automated clearance, access, detention, or security findings.",
            "Dual-control and required approvals are human/process responsibilities enforced by policy and system gates where configured.",
            "Cues do not establish facts, intent, deception, or truthfulness.",
        ],
    ),
    "leg": Disclaimer(
        id="cueliez-disclaimer-leg",
        title="CueLiez Disclaimer — Legal / Investigative Interview Context",
        version=VERSION,
        domain="leg",
        body="Legal/investigative use remains subject to the general disclaimer and applicable law, rights, and procedural requirements.",
        bullets=[
            "Not a legal finding, not evidence of guilt/innocence, and not a determination of deception.",
            "Not for automated detention, charging, or clearance decisions.",
            "Operators must follow required notices, rights, and documentation procedures for the jurisdiction/context.",
        ],
    ),
    "med": Disclaimer(
        id="cueliez-disclaimer-med",
        title="CueLiez Disclaimer — Medical / Clinical Support Context",
        version=VERSION,
        domain="med",
        body="Clinical support use remains subject to the general disclaimer. CueLiez is not a medical device.",
        bullets=[
            "Not for diagnosis, treatment decisions, symptom-validity judgments, or credibility determinations.",
            "Not for automated clinical decisions; qualified clinical judgment and applicable pathways control care.",
            "Any feature summaries (audio/visual/physiological) are non-diagnostic observations only when lawfully obtained and consent-governed.",
        ],
    ),
    "thrp": Disclaimer(
        id="cueliez-disclaimer-thrp",
        title="CueLiez Disclaimer — Therapy / Supportive Context",
        version=VERSION,
        domain="thrp",
        body="Therapy/supportive use remains subject to the general disclaimer. CueLiez is not a medical device.",
        bullets=[
            "Not for diagnosis, risk adjudication, credibility determinations, or automated care decisions.",
            "Cues are communication/process prompts and must not be treated as evidence of intent or truthfulness.",
            "Use must remain supportive, human-led, and consistent with applicable ethical/legal/safety obligations.",
        ],
    ),
}


def domain_disclaimer(domain: str, version: str = VERSION) -> Disclaimer:
    key = (domain or "").strip().lower()
    if key not in _DOMAIN:
        raise KeyError(f"Unknown disclaimer domain {domain!r}. Available: {sorted(_DOMAIN)}")
    d = _DOMAIN[key]
    return Disclaimer(**{**d.to_dict(), "version": version})


def get_disclaimer_bundle(domain: Optional[str] = None, *, version: str = VERSION) -> List[Disclaimer]:
    out = [general_disclaimer(version=version)]
    if domain and domain.strip().lower() not in ("", "general"):
        out.append(domain_disclaimer(domain, version=version))
    return out


def render_disclaimer(d: Disclaimer) -> str:
    lines = [f"# {d.title}", "", f"- **ID:** `{d.id}`", f"- **Version:** `{d.version}`", f"- **Domain:** `{d.domain}`", "", d.body, "", "## Key points"]
    for b in d.bullets:
        lines.append(f"- {b}")
    return "\n".join(lines) + "\n"
