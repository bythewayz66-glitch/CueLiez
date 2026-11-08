# Observer Inventory

**Product:** CueLiez (Cue + Legal Interview Engine) — observations/cues only (probabilistic indicators). Not a lie detector, not a finding.

This inventory reflects the current implementation in `src/cueliez/observations/` and pack definitions in `src/cueliez/packs/definitions.py`.

## Contract (all observers)
- Emit gate-compatible observations: neutral `label`, `confidence.score` in `[0,1]`, non-empty `confidence.model_id` (versioned), `method`, `category`, `evidence` (dict).
- Deterministic `cue_id` and `priority` (`normal`|`high`) are included (see `agent_notes/2026-11-08_0651_kilo_to_all_cue-id-priority-contract-v2.md`).
- Insufficient/thin data → emit **no** observations (do not invent weak cues).
- Rule/heuristic observers only (no external ML model required at runtime). Future ML/LLM-assisted observers must be versioned, feature-flagged/test-only as applicable, and emit the same contract.

## Model ID / version pattern
- `confidence.model_id` = observer `method_id` (versioned), e.g. `cueliez.observations.linguistic.hedging/v1`.
- `confidence.version` may be included (default `v1` from `make_observation`).

## Default runners
- **`default_runner()`**: all core text + consistency + behavioral transcript observers below (20 observers). No prosody/visual/physiological feature observers.
- **`full_runner()`**: `default_runner()` + prosody/visual/physiological feature observers (9 additional). Feature observers emit nothing when required metadata is absent.
- **Convergence**: `add_convergence_observations` / `CrossModalConvergenceObserver` (`cueliez.observations.multimodal.convergence/v1`, category `multimodal`) can add turn-level convergence cues from existing observations (post-run helper).

## Off by default (consent/policy controlled)
Prosody, visual, and physiological feature observers are **not** in `default_runner()` and are **off by default** in domain packs (`include_feature_observers=False`). Enable only via explicit, consent-controlled paths/policy support.

ML/LLM-assisted observers (Phase 1 design/prototype, e.g. `observations.assisted`) are **disabled by default** (`ASSISTED_OBSERVERS_ENABLED=False`), not in any runner/pack, and make **no external ML calls** in the production path. See `docs/design/ml_llm_assisted_observers_phase1.md`.

| Method ID | Category | Type | Notes |
|---|---|---|---|
| `cueliez.observations.prosody.variability_shift/v1` | prosody | rule/feature | Requires caller-provided acoustic features |
| `cueliez.observations.prosody.pause_pattern/v1` | prosody | rule/feature | Requires pause/silence metadata |
| `cueliez.observations.prosody.voice_feature_shift/v1` | prosody | rule/feature | Requires named acoustic features |
| `cueliez.observations.visual.gaze_pattern/v1` | visual | rule/feature | Requires annotated visual features |
| `cueliez.observations.visual.blink_rate/v1` | visual | rule/feature | Requires annotated visual features |
| `cueliez.observations.visual.motor_activity/v1` | visual | rule/feature | Requires annotated visual features |
| `cueliez.observations.physiological.heart_rate_shift/v1` | physiological | rule/feature | Requires consent-governed measurement summaries |
| `cueliez.observations.physiological.hrv_shift/v1` | physiological | rule/feature | Requires consent-governed measurement summaries |
| `cueliez.observations.physiological.electrodermal_shift/v1` | physiological | rule/feature | Requires consent-governed measurement summaries |

## Core observers (default runner + packs)

| Method ID | Category | Type | Default packs |
|---|---|---|---|
| `cueliez.observations.linguistic.hedging/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.linguistic.pronoun_distancing/v1` | linguistic | rule | gov, leg |
| `cueliez.observations.linguistic.negation_density/v1` | linguistic | rule | gov, leg |
| `cueliez.observations.linguistic.detail_vagueness/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.linguistic.certainty_swing/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.linguistic.minimization/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.linguistic.passive_voice_proxy/v1` | linguistic | rule | gov, leg |
| `cueliez.observations.linguistic.overjustification/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.linguistic.memory_qualifiers/v1` | linguistic | rule | gov, leg, med, thrp |
| `cueliez.observations.consistency.claim_conflict/v1` | consistency | rule | gov, leg, med (`priority=high` for possible statement conflicts) |
| `cueliez.observations.consistency.timeline_inconsistency/v1` | consistency | rule | gov, leg, med |
| `cueliez.observations.consistency.detail_drift/v1` | consistency | rule | gov, leg, med |
| `cueliez.observations.consistency.location_divergence/v1` | consistency | rule | gov, leg |
| `cueliez.observations.consistency.self_reference_shift/v1` | consistency | rule | gov, leg, thrp |
| `cueliez.observations.behavioral.response_latency/v1` | behavioral | rule | gov, leg, med, thrp |
| `cueliez.observations.behavioral.answer_length_variance/v1` | behavioral | rule | gov, leg, med, thrp |
| `cueliez.observations.behavioral.evasion_markers/v1` | behavioral | rule | gov, leg, med |
| `cueliez.observations.behavioral.speech_rate_shift/v1` | behavioral | rule | gov, leg, med, thrp |
| `cueliez.observations.behavioral.filled_pauses/v1` | behavioral | rule | gov, leg, med, thrp |
| `cueliez.observations.behavioral.interruption_overlap/v1` | behavioral | rule | gov, leg |

## Hardening notes (2026-11-08 owner transcript pass)
- **Hedging (`linguistic.hedging/v1`)**: time-approximation tokens (`about`/`around`/`roughly`/`approximately`) immediately followed by a clock-time expression (e.g., "around nine-thirty") are excluded from hedging counts to reduce false positives on ordinary time approximations; genuine hedges still fire. Threshold constants: `src/cueliez/observations/thresholds.py` (`HEDGING_*`).
- **Timeline (`consistency.timeline_inconsistency/v1`)**: recognizes digit clock times and spelled-out hour/minute references in time-context (e.g., "at eight", "eight-thirty"). Emits neutral `multiple_time_references_present` with source quotes. Precision: 2+ distinct digit clock times (legacy) OR 4+ distinct total time refs; avoids over-cueing short sequential accounts. Multiple times may describe a sequence (not a conflict assertion).
- **Limitation (conflict phrasing)**: semantic contradictions expressed without affirmation/negation key overlap (e.g., "whole time until ten" vs "gone by eight-thirty") may not trigger `claim_conflict`/`detail_drift`; the timeline cue can still surface time references for review. Observers do not assert deception.

## Confidence scores and calibration (Phase 3)
- `confidence.score` is a heuristic, rule-derived signal strength in `[0.0, 1.0]`, clamped/validated by `make_observation`. Scores are **not** statistically calibrated to ground-truth outcomes and must **not** be interpreted as probability of deception, credibility, guilt, intent, or any finding.
- `confidence.model_id` identifies the versioned observation method (not an external ML model in the production path).
- Insufficient/thin data yields no observations (not low-confidence noise). Same input + same method versions produce deterministic `cue_id` and stable observation content.

## Pack summary
- **gov** (government, 20 core observers): text-only by default; dual-control is a process expectation for high-priority cues before sealing in government mode (enforced by iceman/gates, not by observers).
- **leg** (interrogation, 20): text-only by default.
- **med** (clinical, 14): curated text subset; text-only by default.
- **thrp** (therapy, 11): curated supportive subset; text-only by default.

See `cueliez.packs.list_packs()` / `get_pack()` and `tests/test_packs.py` for authoritative membership and language/gate expectations.
