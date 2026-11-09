# CueLiez Training & Certification Scope (Important Boundary)

## What exists today (real)
CueLiez provides **training content and gate integration**:
- Domain training modules (gov/leg/med/thrp) with required topics, responsibilities, prohibited-use review, and assessment checks.
- Training acknowledgement validation (`TrainingAcknowledgement`, `validate_training_ack`) and gate application (`apply_training_to_gate_state`, CLI/training gate fields).
- Documentation templates for training and consent.

This supports **operator competency workflows** for observation/cue-only, human-led use.

## What “full certification program” means (not claimed unless implemented)
A full certification program requires product/institutional infrastructure beyond content and gate hooks, such as:
- Persistent training records and operator transcript history
- Credential/certificate issuance, verification, status, and revocation
- Expiry/renewal/recertification policy and enforcement
- Authorized trainer/proctor governance, RBAC, and auditable admin actions
- Assessment delivery/scoring (not caller-declared only), where applicable
- Identity/HR/privacy controls and records retention handling

**CueLiez must not claim a full certification program or certify legal/clinical/deception-detection competence** unless those capabilities are actually implemented, governed, and validated for the deployment context.

## Minimal persistent records model (technical support, not a full LMS)
`src/cueliez/compliance/records.py` provides a **minimal file-backed training credential record model** (JSONL, append-only events, tamper-evident record hashes) to support:
- issuing/verifying/revoking credentials
- expiry/status checks
- producing gate-compatible training acknowledgement data

This is **technical record support**, not a complete LMS, governance platform, or legal certification authority.

## Language/safety rules
All training/cert materials and records must remain observation/cue-only and must never imply:
- lie detection or deception/truth determination
- guilt findings or automated legal decisions
- clinical diagnosis or medical-device capability
- polygraph substitution
