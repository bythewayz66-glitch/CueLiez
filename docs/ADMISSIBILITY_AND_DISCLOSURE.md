# Admissibility & Disclosure Guide (v1)

**Status:** v1 (technical accuracy: iceman-owned for seal/gate/hash sections). Glyph may align export/presentation wording.  
**Rule:** Observation and cues only — never findings. See `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

## Explicit non-finding statement

CueLiez produces **observed indicators and cues** for human review. It is **not a lie detector**, **not a polygraph or polygraph substitute**, **not a truth score**, and **not a medical device**. Sealed packages are **not** legal findings, diagnoses, guilt determinations, or confirmations of deception/truthfulness. Automated detention, charge, clearance, or similar decisions are prohibited uses.

## What a sealed package contains

A sealed package (from `seal_observation_package` / `session.seal`) is a self-describing JSON artifact. Canonical schema: `docs/schemas/sealed_package_v1.md` (`schema_version` `"1.0"`).

- **Identity/version:** `schema_version`, `product` (`CueLiez`), `product_version`
- **Epistemic (forced at seal):** `epistemic_status="observed_indicator"`, `origin="grounded"`, `is_definitive_finding=false`
- **Disclaimer:** canonical `disclaimer` text and `disclaimer_version` (versioned identifier for the canonical seal disclaimer; matches `cueliez.gates.DISCLAIMER_VERSION`)
- **Integrity:** `package_hash` (SHA-256 hex), `sealed_at` (Unix timestamp), `sealed=true`, optional `package_signature` (pluggable; excluded from content hash)
- **Process/gates:** `gate_state` snapshot (mode; consent + attester + timestamp; training acknowledgement + version; `dual_control_records`; `intended_uses`; subject/jurisdiction/operator identifiers when provided; requirement flags)
- **System observations/cues:** `observations` (neutral, confidence-scored; each has `label`, `confidence.score` in [0,1], non-empty `confidence.model_id`, `method`, `category`) and optional `cues`
- **Human context:** optional `officer_cue_notes` (human-authored actions/notes on cues; attached **before** seal; not system findings)
- **Safety metadata:** `firewall` (contamination/gate recheck flags), optional `annotations` (banned verdict keys rejected)

## What it does not contain

- No verdict labels, truth scores, deception confirmations, guilt/not-guilt outputs, diagnoses, or legal findings as system outputs.
- No post-seal mutation of observations/epistemic fields via normal APIs. Officer notes must be attached before seal.

## Process evidence (gates)

`gate_state` records captured process controls (not a system verdict):

| Control | High-stakes modes | Evidence fields |
|---------|-------------------|-----------------|
| Affirmative consent + attester | interrogation, therapy, clinical, government | `consent`, `consent_recorded_at`, `consent_attested_by` |
| Training acknowledgement + version | same | `training_acknowledged`, `training_version` |
| Dual control (high-priority cues) | government | `dual_control_records[]` (distinct officer IDs per cue). `high_priority_cue_ids` may be explicit or extracted from `cues`/`observations` with `priority` `high`/`critical` and `cue_id`/`id`. |
| Prohibited uses | checked | `intended_uses`; prohibited uses fail closed |

Fail-closed: required gates missing in applicable high-stakes modes → seal/start/observe refuses with a stable `GateError` code.

## Hash and signature verification

- `package_hash` = SHA-256 of canonical JSON (sorted keys, compact separators, UTF-8) over package content **excluding** `package_hash`, `content_hash`, `sealed_at`, `package_signature`.
- Same canonical input ⇒ same hash. `gate_state`, `officer_cue_notes`, and observations are included when present.
- `package_signature` is **optional** (default `null`) and **excluded from `package_hash`**. Real cryptographic signing is pluggable; absence of a signer never breaks sealing.

**Verification flow (recommended):**
1. **Hash first:** load JSON and verify `package_hash` (`cueliez.gates.verify_package_hash` / `compute_package_hash`, or offline canonical SHA-256). If the hash fails, treat content as not integrity-verified.
2. **Signature optional:** if `package_signature` is present and a verifier is configured, verify the signature against the package/hash per the signature scheme. Signature verification is independent of, and does not replace, hash verification.
3. **Forced fields:** confirm `epistemic_status == "observed_indicator"`, `is_definitive_finding == false`, disclaimer and `disclaimer_version` present.

## Officer notes vs system observations

- **System observations/cues:** produced by observers/delivery; probabilistic, neutral labels; confidence/model metadata.
- **`officer_cue_notes`:** human-authored responses/actions (acknowledged/dismissed/noted, optional text) tied to `cue_id`s. They are review context, **not** system findings, and must be framed as human notes in exports/disclosure.

## Recommended disclosure handling (high level)

- Disclose as an observation/cue artifact with disclaimer and gate/process state visible.
- Do **not** describe as proof of deception, truthfulness, guilt, innocence, or diagnosis.
- Preserve canonical JSON + `package_hash` (and any signature, if used) for review. Human-readable summaries are aids, not substitutes for the canonical package.
- Follow jurisdictional/policy requirements for consent, recording, retention, and evidence handling (outside library scope).

## Session lifecycle (integration)

Use `cueliez.session.start_session` / `assert_can_observe` before observation in high-stakes modes, and `session.seal` / `seal_observation_package` for sealing. CLI/UI should not bypass gate checks. See `docs/GATE_ERROR_CODES.md` and `agent_notes/` for integration contracts.
