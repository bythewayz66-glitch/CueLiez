# CueLiez Demo Training (Presenter)

**Purpose:** Train you to demonstrate CueLiez accurately, safely, and in compliance with its observation/cue-only model.

## 1) What CueLiez is (use this framing)

- **CueLiez** = **Cue** + **L**egal **I**nterview **E**ngine.
- It observes behavioural/linguistic signals and testimony-consistency patterns in interview contexts.
- It presents **cues and observations** to a qualified professional to support **human-led** questioning and documentation.
- Outputs are **probabilistic indicators** with confidence and method context — not findings.
- The system includes **hard gates** (consent, training, dual-control where required, prohibited-use enforcement) and **sealed observed-indicator records**.

## 2) What CueLiez is NOT (never claim)

| Never say / imply | Say instead |
|---|---|
| Lie detector / truth detector / truth machine | Observation and cue support for interviews |
| Detects lies / lie detection | Observes signals and testimony patterns; presents cues |
| Confirms deception / caught lying | Possible inconsistency or indicator for human review |
| Subject is lying / truthful / guilty / innocent (as system output) | Cues may help a professional decide what to clarify; humans judge |
| Polygraph / polygraph substitute | Not a polygraph; different purpose and claims |
| Diagnosis / medical or legal finding | Not diagnostic; not a legal finding; not for automated decisions |

## 3) Core demo competencies

You should be able to:

1. **Explain the value without overclaiming:** clearer inquiry, better follow-up questions, auditable observed-indicator records — for both the guilty and the innocent.
2. **Show a cue, not a verdict:** point to labels/evidence/confidence/cue text; emphasize “review required, not a finding.”
3. **Show the guardrails:** consent required in high-stakes modes, training gates, government dual-control, prohibited uses, seal hardening (`observed_indicator`, `is_definitive_finding=false`).
4. **Handle pushback:** when asked “so it detects lies?”, answer clearly and pivot to what it actually does.
5. **Demo safely:** use synthetic/sample data unless you have explicit authorization and appropriate consent/policy coverage. Never expose sensitive real interview data.

## 4) Demo safety and ethics

- **Data:** Prefer synthetic transcripts. If using realistic examples, de-identify and ensure authorization/consent/policy compliance.
- **Context:** Match the demo pack to the audience (gov/leg/med/thrp) and explain mode/gate differences.
- **Clinical/therapy demos:** be especially careful — no diagnosis, no credibility judgments, no risk adjudication claims.
- **Legal/government demos:** no claims of automated detention/charging/clearance/security findings.
- **Records:** if showing sealing/storage, explain that sealed packages preserve observed indicators with disclaimers, not verdicts.

## 5) Technical points you can demonstrate

- **Observation methods/modalities:** linguistic, testimony consistency, behavioral/metadata cues; optional prosody/visual/physiological feature adapters (caller-provided, consent-governed, non-diagnostic) where appropriate.
- **Domain cue packs:** `gov`, `leg`, `med`, `thrp` (mode-mapped observers/guidance).
- **Delivery:** onscreen cue panel/text/HTML and audio cue assets (priority tones + scripts/manifests) for the professional.
- **Consent/training/disclaimers:** general + domain supplements, workflow validation, gate integration.
- **Tests/compliance:** strict tests cover gates, consent, language/verdict rejection, and observation modules.

## 6) Presenter assessment (self-check)

Before demoing, confirm you can answer “yes”:

- [ ] I can give the 10-second and 26-second descriptions without “lie detector” framing.
- [ ] I can explain an observation (label, confidence, evidence, cue) as a prompt for human review.
- [ ] I can show at least one guardrail (consent gate, seal hardening, or prohibited use).
- [ ] I have a safe synthetic scenario ready.
- [ ] I know how to answer “Can this tell if someone is lying?” clearly and calmly.
- [ ] I will not make domain-specific legal/clinical claims beyond the product’s compliant scope.
