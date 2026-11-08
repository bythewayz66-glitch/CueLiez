# Sealed Package Schema v1 (`schema_version`: `1.0`)

**Status:** Stable v1. Only bump `schema_version` with an orchestrator note.  
**Producer:** `cueliez.gates.seal_observation_package` / `cueliez.session.seal`  
**Framing:** observation and cues only — never findings.

## Required / canonical keys (set or enforced at seal)

| Key | Type | Notes |
|-----|------|-------|
| `schema_version` | string | `"1.0"` |
| `product` | string | `"CueLiez"` |
| `product_version` | string | Package version |
| `epistemic_status` | string | **Forced** to `"observed_indicator"` |
| `origin` | string | `"grounded"` |
| `is_definitive_finding` | boolean | **Forced** to `false` |
| `disclaimer` | string | Canonical disclaimer text |
| `disclaimer_version` | string | Canonical disclaimer version identifier (matches `cueliez.gates.DISCLAIMER_VERSION`) |
| `sealed` | boolean | `true` |
| `sealed_at` | number | Unix timestamp (set at seal; **excluded from hash**) |
| `package_hash` | string | SHA-256 hex (64 chars); **excluded from hash input** |
| `gate_state` | object | Full `SessionGateState` snapshot (see below) |
| `observations` | array | Gate-validated observation dicts (canonical key; `detections` normalized) |
| `firewall` | object | `contamination_check="passed"`, recheck flags, `gate_state_captured` |

## Optional / preserved keys

| Key | Type | Notes |
|-----|------|-------|
| `annotations` | object | Non-verdict metadata; banned verdict keys rejected |
| `cues` | array | Delivery cues (when attached); used for high-priority dual-control extraction |
| `officer_cue_notes` | array | **Human** notes/actions; attach **before** seal; preserved; included in hash |
| `session_id` | string | Optional |
| `package_signature` | object\|null | Optional pluggable signature (default `null`/absent) |

## `gate_state` (self-describing)

`mode`, `consent`, `consent_recorded_at`, `consent_attested_by`, `subject_id`, `jurisdiction`, `operator_id`, `dual_control_records[]` (`cue_id`, `first_officer_id`, `second_officer_id`, `acknowledged_at`, `notes`), `intended_uses[]`, `training_acknowledged`, `training_version`, `requirements{consent_required,training_required,dual_control_required}`.

## Observation contract (each entry)

- Neutral non-empty `label` (no verdict labels)
- `confidence.score` in `[0,1]`, non-empty `confidence.model_id`
- Non-empty `method`, non-empty `category`
- `evidence`/other fields as produced

## Hashing

- Algorithm: SHA-256 of canonical JSON (sorted keys, compact separators, UTF-8) over the package **excluding** `package_hash`, `content_hash`, `sealed_at`.
- Identical canonical input ⇒ identical `package_hash`. `officer_cue_notes` and `gate_state` are included when present.

## Immutability (normal API)

Sealed packages must not be mutated via normal helpers. `attach_officer_cue_notes` refuses when sealed (`sealed=true` or hash+sealed_at+observed_indicator).
