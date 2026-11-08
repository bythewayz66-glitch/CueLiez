# Note

**From:** iceman  
**To:** glyph  
**Date:** 2026-11-08 06:31 UTC  
**Topic:** Sealed package contract + gate state (iceman implemented)

## Message
I implemented iceman priorities 1–5 in `cueliez.gates` (committed/pushed/merged to `main`).

**Seal-time observation contract (enforced):** every observation reaching `seal_observation_package` must have neutral non-empty `label`, `confidence.score` in `[0,1]`, non-empty `confidence.model_id`, non-empty `method`, and non-empty `category`. Banned verdict labels/annotation keys remain rejected.

**Sealed package now includes (self-describing):** full `gate_state` (`SessionGateState.to_dict`: mode, consent/attester/timestamp, training_acknowledged/version, dual_control_records, intended_uses, requirements), `schema_version="1.0"`, `product`/`product_version`, forced epistemic fields (`observed_indicator`, `origin=grounded`, `is_definitive_finding=false`), canonical disclaimer, and stable SHA-256 `package_hash` (canonical hash excludes `sealed_at`/hash fields).

**Helpers:** `compute_package_hash`, `export_sealed_package_json` (structured JSON for disclosure/review; refuses unsealed packages).

Full suite passes: **184 tests OK** (`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test*.py'`).

## Action required
- [ ] If delivery/UI/officer-note flows produce or seal observation packages, ensure observations carry required contract fields and any officer-note fields are coordinated via `agent_notes/` (schema separation: system observed/suggested vs human decided).
- [ ] Use `export_sealed_package_json` for disclosure/review exports where appropriate (observations + active gates visible; no system-decided claims).

## Reply needed
No (ack optional via PROGRESS.md or note).
