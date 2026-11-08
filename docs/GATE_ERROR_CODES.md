# Gate Error Codes

Stable `GateError.code` strings raised by `cueliez.gates` / session/seal flows. Tests assert key codes; do not rename without coordination.

| Code | Meaning |
|------|---------|
| `annotations_invalid` | `annotations` must be a dict |
| `confidence_out_of_range` | `confidence.score` not in `[0,1]` |
| `connector_auth_failed` | Connector authentication/authorization failed (env/credentials) |
| `connector_config_missing` | Required connector configuration (e.g. env var/endpoint) missing |
| `connector_network_error` | Connector network/transport error (mocked in tests) |
| `connector_validation_failed` | Connector payload/response validation failed |
| `consent_attester_required` | `record_consent` requires non-empty attester |
| `consent_required` | Affirmative consent/attester required for mode/action |
| `contamination_attempt` | Banned annotation key (verdict/definitive claim) |
| `definitive_finding_forbidden` | `is_definitive_finding=true` not allowed |
| `dual_control_ids_required` | Both dual-control officer IDs required |
| `dual_control_incomplete` | Missing dual-control records for high-priority cue IDs |
| `dual_control_not_applicable` | Dual control only for applicable modes (e.g. government) |
| `dual_control_same_officer` | Dual control requires two distinct IDs |
| `epistemic_status_forbidden` | Package epistemic status is a forbidden finding class |
| `export_invalid` | Export requires a sealed observed-indicator package dict |
| `gate_state_required` | Session gate state required for a gate check |
| `ingest_epistemic_invalid` | Ingested package epistemic/disclaimer fields invalid (non-finding contract) |
| `ingest_hash_mismatch` | Ingested package hash verification failed |
| `ingest_invalid_package` | Ingest requires a valid package dict |
| `ingest_not_sealed` | Ingest requires a sealed package |
| `invalid_confidence_score` | `confidence.score` not numeric |
| `jurisdiction_approval_required` | Jurisdiction approval required before enabling a gated input modality |
| `jurisdiction_required` | Jurisdiction must be recorded before enabling a gated input modality |
| `missing_category` | Observation missing `category` |
| `missing_confidence` | Observation missing confidence object |
| `missing_confidence_score` | Observation missing `confidence.score` |
| `missing_label` | Observation missing neutral label |
| `missing_method` | Observation missing `method` |
| `missing_model_id` | Observation missing `confidence.model_id` |
| `modality_consent_required` | Explicit consent required before enabling a gated input modality |
| `observation_invalid` | Observation entry not a dict |
| `observations_invalid` | `observations`/`detections` must be a list |
| `package_sealed` | Mutation/re-seal refused on sealed package |
| `prohibited_use` | Intended use is prohibited by policy |
| `seal_invalid` | Seal input must be a dict |
| `training_required` | Training acknowledgement required for mode |
| `training_version_required` | Training version required when acknowledged |
| `unsupported_gated_modality` | Modality not in supported gated input modalities |
| `verdict_language` | Forbidden verdict label in observation |
