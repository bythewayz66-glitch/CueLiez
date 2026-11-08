# Deployment, Privacy, and Custody (v1 guidance)

**Status:** Documentation posture for first-pilot planning (`generic`, `interrogation` modes). Not legal advice.  
**Rule:** Observation and cues only — never findings. See `AGENTS.md`, `docs/LANGUAGE_RULES.md`, `docs/OWNER_DECISIONS.md`, `docs/ADMISSIBILITY_AND_DISCLOSURE.md`.

## Deployment posture (on-prem / private-cloud first)

- **First pilot:** on-premises or private-cloud processing preferred. **No public SaaS in v1**.
- **CJIS-equivalent readiness (posture):** deployments handling criminal justice information should follow applicable CJIS Security Policy / agency requirements (access control, encryption in transit/at rest, audit logging, personnel screening, incident response) as implemented by the deploying organization and environment. This library provides sealed observation artifacts; it does not itself certify CJIS compliance.
- **Data location:** transcript/observation processing and sealed artifacts should remain within the authorized environment boundary (agency/on-prem/private-cloud). Avoid sending interview content to public model endpoints for production sealing paths.
- **Network:** support air-gapped or restricted-network workflows where feasible (local processing, local export).

## Access controls and retention

- **Access controls (operational):** restrict access to transcripts, unsealed packages, sealed packages, and officer notes to authorized roles; enforce least privilege, MFA/strong authentication where applicable, and audit logging in the hosting/workflow system. Control who can `start_session`/seal, attach notes (pre-seal), export, and transmit to RMS/case systems.
- **Retention (operational):** define retention periods per jurisdiction/policy/case type (e.g., investigative, administrative, training/evaluation contexts as applicable); apply legal holds where required; document deletion/archival procedures. This library does not enforce retention schedules or deletion — operators/systems must.
- **Data handling:** minimize copies; encrypt at rest/in transit per environment policy; avoid exporting sensitive content to unapproved systems.
- **Deletion/export:** when exporting, preserve canonical sealed JSON (`package_hash`, gate state, disclaimer/version) as the original artifact; summaries are aids, not replacements. For RMS/case attachment, transmit the sealed package as an original artifact and validate integrity on ingest (`validate_sealed_package_ingest`).

## Sealed-package custody

- Attach sealed packages as **original artifacts** (canonical JSON) rather than derivative interpretations.
- Preserve integrity evidence: `package_hash` (SHA-256 over canonical content excluding `sealed_at`/hash/signature fields), `sealed_at`, `schema_version`, `disclaimer`/`disclaimer_version`, `gate_state`, and any `package_signature` (optional).
- **Officer notes** (`officer_cue_notes`) are human-authored and must be attached **before** seal; sealed packages refuse post-seal mutation via normal helpers.
- Use `cueliez.gates.verify_package_hash` / `custody_receipt` for review support (no findings).

## Integration readiness (transcript ingest)

- **Current:** transcript ingest accepts JSON sequences/compatible structures used by `ObservationRunner` (turn mappings with role/text and optional metadata). No live Axon/RMS integration required.
- **Future integrations (expectations):** provide deterministic transcript export (ordered turns, stable IDs/timestamps where available, speaker/role, text). Map to observation inputs without adding verdict fields. Preserve chain-of-custody metadata outside the sealed observation content as appropriate for the evidence system.
- Packages should remain easy to attach to RMS/case/evidence workflows as canonical JSON artifacts.

## Operational readiness checklist (on-prem / private-cloud)

- [ ] **Environment boundary:** processing and storage confined to authorized on-prem/private-cloud (no public SaaS for production interview content in v1).
- [ ] **Configuration:** connector/endpoints/credentials supplied via environment/config management (no hardcoded secrets); verify `connector_config_missing`/`connector_auth_failed` handling.
- [ ] **Gates:** consent/attester/training (and government dual-control for high-priority cues) enforced before seal; gated modalities require explicit consent + jurisdiction validation before enablement.
- [ ] **Integrity:** verify sealed packages with `verify_package_hash` / `validate_sealed_package_ingest`; preserve `package_hash`, `sealed_at`, `disclaimer_version`, `gate_state`.
- [ ] **Custody:** attach sealed JSON as original artifact; attach `officer_cue_notes` only before seal; retain audit logs/access records per policy.
- [ ] **RMS/case/evidence attachment:** use connector ingest validation; store original sealed artifact (not derivative interpretation) with chain-of-custody metadata managed by the receiving system.
- [ ] **CJIS/equivalent controls (where applicable):** implement agency-required access control, encryption, auditing, personnel/incident processes; this library does not certify compliance.
