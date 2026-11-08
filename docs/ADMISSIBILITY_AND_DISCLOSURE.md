# Admissibility & Disclosure (Technical Stub)

**Status:** Technical skeleton (iceman-owned accuracy for seal/gate sections). Glyph may align export/presentation wording.  
**Rule:** Observation and cues only — never findings. See `AGENTS.md` and `docs/LANGUAGE_RULES.md`.

## What a sealed package contains

A sealed package (from `seal_observation_package`) is a self-describing JSON artifact of *observed indicators* and process metadata. It may include:

- `schema_version`, `product` (`CueLiez`), `product_version`
- `observations` — neutral, confidence-scored indicators (each with `label`, `confidence.score` in [0,1], non-empty `confidence.model_id`, `method`, `category`, and evidence)
- `annotations` — optional non-verdict metadata (banned verdict keys rejected at seal)
- `cues` — optional delivery cues (when produced/attached by delivery flows)
- `gate_state` — full session gate snapshot (mode; consent/attester/timestamp; training acknowledgement/version; `dual_control_records`; `intended_uses`; subject/jurisdiction/operator identifiers when provided; requirement flags)
- `officer_cue_notes` — optional **human** notes/actions on cues, attached **before** seal (not system findings)
- `epistemic_status` (`observed_indicator`), `origin` (`grounded`), `is_definitive_finding` (`false`)
- canonical `disclaimer`
- `package_hash` (SHA-256 hex) and `sealed_at`
- `sealed: true`, `firewall` (contamination/gate recheck flags)

## What it is not

- Not a lie detector, polygraph, truth score, or medical device.
- Not a legal finding, diagnosis, guilt determination, or confirmation of deception.
- Not an automated detention/charge/clearance decision. Human judgment is required.

## Gate fields and process evidence

`gate_state` records what process controls were captured for the session (as provided to the system):

- **Consent (high-stakes modes):** `consent`, `consent_recorded_at`, `consent_attested_by` (non-empty attester required where applicable).
- **Training (high-stakes modes):** `training_acknowledged`, `training_version`.
- **Dual control (government, high-priority cues):** `dual_control_records` (distinct officer IDs per required cue). `high_priority_cue_ids` may be supplied at seal or extracted from package `cues`/`observations` entries with `priority` `high`/`critical` and `cue_id`/`id`.
- **Intended uses:** recorded; prohibited uses fail closed.

Gate checks are fail-closed for required high-stakes modes. Presence of gate fields documents process state; it does not constitute a system verdict.

## `package_hash` meaning

`package_hash` is SHA-256 over a stable canonical JSON serialization of the package content, **excluding** volatile/hash fields (`sealed_at`, `package_hash`/`content_hash`). It supports integrity review of the sealed content. Identical canonical input yields the same hash.

## `officer_cue_notes` (human notes)

`officer_cue_notes` are officer-authored actions/notes in response to observation cues (e.g., acknowledged, dismissed, noted). They are human review context, not system findings, and must be attached **before** seal. Sealed packages refuse post-seal note attachment via normal helpers.

## Disclosure handling (high level)

- Disclose the package as an observation/cue artifact with the included disclaimer and gate state.
- Do not represent outputs as proof of deception, truthfulness, guilt, or diagnosis.
- Preserve the canonical package (JSON) and hash for review; use human-readable summaries only as aids that retain the same framing.
- Follow jurisdictional/policy requirements for consent, recording, and evidence handling (outside this library’s scope).

## Session lifecycle helpers (Sprint 3)

`cueliez.session`: `start_session(state)` / `assert_can_observe(state)` run fail-closed consent/training/prohibited-use checks before observation; `seal(...)` wraps `seal_observation_package`. CLI/UI integrations should use these paths for high-stakes modes.
