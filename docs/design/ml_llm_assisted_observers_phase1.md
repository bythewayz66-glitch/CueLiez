# Phase 1 Design — ML/LLM-Assisted Observers (Feature-Flagged, Not Enabled)

**Status:** design + optional prototype interface only. **Not enabled by default. No external ML in the production path.** Rule/heuristic observers remain the baseline for `default_runner()`/packs.

## Scope (high-value signals)
Candidate signals for future assisted observation (same neutral cue/label/evidence contract):
- `hedging_language_present` (linguistic)
- `distancing_language_present` / pronoun distancing (linguistic)
- `low_specificity_language_present` / detail vagueness (linguistic)
- `possible_statement_conflict` / claim conflicts (consistency)
- `multiple_time_references_present` / timeline inconsistency (consistency)

All outputs must remain **probabilistic observations/cues for human review** — never deception, credibility, guilt, intent, diagnosis, or findings.

## Contract requirements
- Gate-compatible observation: neutral `label`, `confidence.score` in `[0,1]`, non-empty `confidence.model_id`, `method` (versioned), `category`, `evidence` (dict), deterministic `cue_id`, `priority`.
- `confidence.model_id` and `method` must identify the **exact model/method version and provenance** (e.g., `cueliez.observations.linguistic.hedging.assisted/<provider-model>@<version>#<prompt-or-adapter-hash>`). Scores are heuristic/model-derived unless separately validated; document calibration limits (not ground-truth deception probability).
- Feature-flagged: disabled unless explicitly enabled by configuration/policy; never added to `default_runner()` or packs by default. Packs/modes must not implicitly enable assisted observers.
- Provenance in evidence/metadata: model/provider name, version/revision, prompt/adapter version, timestamp, input hash or reference, and any safety filters applied (as appropriate; no sensitive data leakage).

## Safety, privacy, and deployment
- **Production default:** no external LLM/ML calls. Assisted observers, if ever enabled, must run on approved infrastructure (prefer on-prem/private-cloud) with data handling consistent with jurisdiction/policy, consent, and retention controls.
- **No public AI for production implementation code paths** (per repo rules) and no raw sensitive interview data sent to unapproved/public services.
- Fallback: if assisted path is unavailable/disabled/errored, emit no assisted observations (do not fail the run; log/operator note as appropriate) and rely on rule-based baseline.
- Human review required; seals/gates unchanged.

## Prototype status
A minimal disabled interface/registry may exist in code for contract testing only (`observations.assisted` concept). It must not make network calls, must not be wired into `default_runner()`/`full_runner()`/packs, and must be feature-flagged off.
