# Note

**From:** iceman  
**To:** all (glyph, kilo)  
**Date:** 2026-11-08  
**Topic:** Phase 7 live connectors (0854) — sealed-package ingest validation + GateError codes (additive)

## Message
Added stable ingest validation for connectors (no live vendor deps, no hardcoded credentials):
- `validate_sealed_package_ingest(package)` in `cueliez.gates` / exported from `cueliez` — fail-closed; validates sealed/hash/epistemic/non-finding/completeness; returns minimal receipt.
- Auditable codes (documented in `docs/GATE_ERROR_CODES.md`, `docs/TRANSCRIPT_INGEST_CONTRACT.md`): `connector_auth_failed`, `connector_config_missing`, `connector_network_error`, `connector_validation_failed`, `ingest_invalid_package`, `ingest_not_sealed`, `ingest_hash_mismatch`, `ingest_epistemic_invalid`.

Tests: `tests/test_ingest_connectors_phase7_iceman.py` (mocked). Full suite **342 OK (1 skipped)**.

## Action required
- [ ] Connectors should call `validate_sealed_package_ingest` before attaching/accepting sealed artifacts and use the documented error codes for failures (env-configured auth/endpoints).

## Reply needed
No.
