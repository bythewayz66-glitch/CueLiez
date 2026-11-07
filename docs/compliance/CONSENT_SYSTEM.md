# CueLiez Consent System (Workflow Overview)

This document describes the operational consent workflow for CueLiez. It is not legal advice. Required notices, rights, voluntariness rules, and documentation obligations depend on jurisdiction, context, and applicable law/policy.

## Principles

- **Affirmative, attested consent:** In high-stakes modes (government, interrogation/legal, clinical, therapy), consent must be affirmatively recorded with a non-empty `attested_by` professional/operator identifier before start and again checked before seal.
- **Disclosure before reliance:** The general consent/disclosure and applicable domain supplement must be reviewed/provided as required by law/policy before relying on the consent record.
- **No verdict framing:** Consent materials must state that CueLiez is not a lie detector/polygraph/truth machine and does not produce deception, guilt, truth, diagnosis, or automated decisions.
- **Gates enforce, humans administer:** The software enforces gate checks; humans are responsible for providing legally/policy-required notices and confirming workflow steps.

## Forms

1. **General consent/disclosure** (`GENERAL_CONSENT.md`, form `cueliez-consent-general`)
   - Purpose and observation/cue scope
   - Not a lie detector; no verdicts/findings
   - No automated legal/clinical decisions
   - Session records/sealing as observed indicators
   - Human review responsibility
   - Rights/voluntariness handled per applicable law/policy

2. **Domain supplementary consent/disclosure** (select by domain/mode)
   - `gov` / `government`: authority/jurisdiction/scope, dual-control/oversight awareness, records handling, no automated security findings
   - `leg` / `interrogation`: legal/investigative context notices, rights/required notices completed by operator, no legal findings, documentation
   - `med` / `clinical`: not a medical device/diagnostic, communication support only, privacy/health information handling, optional modalities consent-governed/non-diagnostic
   - `thrp` / `therapy`: supportive/non-adversarial use, no diagnosis/credibility/risk adjudication, boundaries/safety/privacy, participation/comfort as applicable

## Workflow

1. Select session mode/domain and confirm lawful/policy basis.
2. Provide/review general consent and the applicable domain supplement; complete jurisdiction/policy-required notices.
3. Capture acknowledgement:
   - required disclosures acknowledged/provided as applicable
   - opportunity for questions provided as applicable
   - voluntariness/required notices handled per law/policy
   - subject affirmation/statement summary (as applicable)
   - **attested_by** (non-empty), subject reference/ID (if applicable), jurisdiction/policy reference
4. Validate the acknowledgement record (all required disclosures, attester, confirmations).
5. Apply to gate state (`cueliez.consent.apply_consent_to_gate_state` / `gates.record_consent`): sets affirmative consent + timestamp + attester.
6. Before seal, gates re-check consent (and training/dual-control/prohibited uses as required).

## Software integration

```python
from cueliez.consent import (
    general_consent_form, domain_supplement, ConsentAcknowledgement,
    validate_acknowledgement, apply_consent_to_gate_state,
)
from cueliez.gates import SessionGateState

state = SessionGateState(mode="interrogation")
form = general_consent_form()  # and/or domain_supplement("leg")
ack = ConsentAcknowledgement(
    form_id=form.id, form_version=form.version,
    attested_by="officer-123", subject_id="subj-1", jurisdiction="example",
    acknowledged_disclosure_ids=[d.id for d in form.disclosures if d.required],
    questions_opportunity_confirmed=True, voluntariness_confirmed=True,
    subject_statement="Affirmation recorded per policy.",
)
record = validate_acknowledgement(form, ack)
apply_consent_to_gate_state(record, state)  # raises if invalid by default
```

## Records

Consent records should capture: form ID/version, domain/mode, subject reference (as permitted), jurisdiction/policy reference, acknowledged disclosures, confirmations, affirmation summary, attester, timestamp, and session/case identifiers as appropriate. Store/retain per applicable law and policy.
