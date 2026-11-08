# Deployment, Privacy, and Custody (v1 guidance)

**Status:** Documentation posture for first-pilot planning (`generic`, `interrogation` modes). Not legal advice.  
**Rule:** Observation and cues only — never findings. See `AGENTS.md`, `docs/LANGUAGE_RULES.md`, `docs/OWNER_DECISIONS.md`, `docs/ADMISSIBILITY_AND_DISCLOSURE.md`.

## Deployment posture (on-prem / private-cloud first)

- **First pilot:** on-premises or private-cloud processing preferred. **No public SaaS in v1**.
- **CJIS-equivalent readiness (posture):** deployments handling criminal justice information should follow applicable CJIS Security Policy / agency requirements (access control, encryption in transit/at rest, audit logging, personnel screening, incident response) as implemented by the deploying organization and environment. This library provides sealed observation artifacts; it does not itself certify CJIS compliance.
- **Data location:** transcript/observation processing and sealed artifacts should remain within the authorized environment boundary (agency/on-prem/private-cloud). Avoid sending interview content to public model endpoints for production sealing paths.
- **Network:** support air-gapped or restricted-network workflows where feasible (local processing, local export).

## Access controls and retention

- **Access controls:** restrict access to sealed packages, transcripts, and officer notes to authorized roles; use least privilege, authentication, and audit trails in the hosting/workflow system.
- **Retention:** define retention periods per jurisdiction/policy/case type; apply legal holds where required. This library does not enforce retention schedules — operators/systems must.
- **Deletion/export:** when exporting, preserve canonical sealed JSON (`package_hash`, gate state, disclaimer/version) as the original artifact; summaries are aids, not replacements.

## Sealed-package custody

- Attach sealed packages as **original artifacts** (canonical JSON) rather than derivative interpretations.
- Preserve integrity evidence: `package_hash` (SHA-256 over canonical content excluding `sealed_at`/hash/signature fields), `sealed_at`, `schema_version`, `disclaimer`/`disclaimer_version`, `gate_state`, and any `package_signature` (optional).
- **Officer notes** (`officer_cue_notes`) are human-authored and must be attached **before** seal; sealed packages refuse post-seal mutation via normal helpers.
- Use `cueliez.gates.verify_package_hash` / `custody_receipt` for review support (no findings).

## Integration readiness (transcript ingest)

- **Current:** transcript ingest accepts JSON sequences/compatible structures used by `ObservationRunner` (turn mappings with role/text and optional metadata). No live Axon/RMS integration required.
- **Future integrations (expectations):** provide deterministic transcript export (ordered turns, stable IDs/timestamps where available, speaker/role, text). Map to observation inputs without adding verdict fields. Preserve chain-of-custody metadata outside the sealed observation content as appropriate for the evidence system.
- Packages should remain easy to attach to RMS/case/evidence workflows as canonical JSON artifacts.
