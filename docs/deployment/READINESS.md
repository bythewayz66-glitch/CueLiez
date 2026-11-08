# Deployment & Operational Readiness (v1, operator-controlled)

**Status:** operational readiness guidance (documentation). Not a certification, legal opinion, or claim of CJIS/FedRAMP/other compliance. Operators and their organizations are responsible for deployment, security, records, consent, and jurisdictional/policy compliance.

## First-pilot posture

- **Modes in pilot messaging/deployment:** `generic` + `interrogation` only (see `docs/OWNER_DECISIONS.md`).
- **Processing:** prefer **on-prem or private-cloud** processing of interview text/transcripts. No public SaaS is required for v1. Gated modalities (audio features, camera, wearable) remain **off by default** and require explicit consent/jurisdiction/policy support before enablement.
- **Artifacts:** sealed `sealed_package.json` is the canonical original artifact (observed indicators/cues, gate/process metadata, `package_hash`). Summaries (MD/HTML, print-to-PDF) are observation-only aids, not findings.

## On-prem / CJIS-aligned operational considerations (guidance)

CueLiez does not implement CJIS controls by itself. For deployments handling criminal justice information or similarly sensitive data, the operator’s environment should address (as applicable):

- **Environment control:** deploy in an operator-approved on-prem/private-cloud environment with documented physical/logical boundaries, hardened hosts/containers, and patch management.
- **Access control:** least privilege, role-based access, MFA where required, and auditable operator identities for package creation/review/export.
- **Encryption & transport:** protect data at rest and in transit per policy (disk/database/file encryption, TLS for any approved connector endpoints). Do not place secrets in package content.
- **Auditability:** retain system/package audit context (`gate_state`, timestamps, hash, officer notes as human records) per records schedules; use `package_hash` for integrity verification of recorded observations/process.
- **Retention & disposal:** follow jurisdiction/agency retention schedules and approved disposal procedures (see below).
- **Training & consent:** enforce required consent/attester/training gates in applicable modes; do not bypass gates.
- **Vendor/connectors:** live Axon/CaseCracker/RMS connectors, when used, require env-based configuration, approved endpoints, credentials managed outside code, and policy review. No hardcoded credentials.

## Data retention and access controls (operator responsibility)

CueLiez does not automatically delete, retain, or authorize access to artifacts. Operators should define:

| Artifact | Typical handling (policy-defined) |
|---|---|
| `sealed_package.json` (canonical) | Retain as original observation/cue artifact per records/evidence policy; restrict access; preserve hash/signature metadata. |
| `*.summary.md` / `*.summary.html` | Optional aids; retain/disclose per policy; never treat as findings or as a substitute for canonical package. |
| Officer note JSON / attached `officer_cue_notes` | Human-authored context; attach before seal; retain as part of case/review record per policy. |
| Local transcript inputs | Handle as sensitive interview material; store/ingest only in approved systems; apply minimization/retention controls. |
| Logs/exports from connectors | May contain metadata; protect and retain per policy; avoid logging secrets or full sensitive content unnecessarily. |

**Access controls:** limit read/write/export to authorized roles (e.g., interviewer, reviewer, records custodian, admin) according to agency policy. Use separate environments/credentials for pilot vs production as appropriate.

## RMS / case / evidence attachment

- Attach **canonical `sealed_package.json`** (and preserve `package_hash`, `schema_version`, `product_version`, disclaimer/epistemic fields, `gate_state`) as an original artifact.
- Summaries are observation-only aids; officer notes are human-authored and not system findings.
- No live RMS connector is required; operator-controlled/manual attachment is supported. Any future live connector must use env-based config, policy approval, and mocked/offline-safe behavior in tests.

## Custody and disclosure

- Present packages as observed indicators/process metadata for human review, not findings/proof of deception/truthfulness.
- Follow jurisdictional/policy requirements for consent, recording, retention, disclosure, and evidence handling.
- Verify integrity via `package_hash` (recorded observations/process), not as proof of subject claims.