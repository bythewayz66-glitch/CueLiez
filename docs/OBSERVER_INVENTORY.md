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

## Default runners (2026-11-25: all observers on by default)
- **`default_runner()`**: **45 observers** — all core text + consistency + behavioral transcript observers, the 4 narrative observers, the new dishonesty-sign observers (hedging cluster, detail-density shift, cross-turn claim restatement, pronoun shift, response-latency shift, speech-rate trend, filled-pause cluster) and the 13 feature observers (prosody/visual/physiological, which emit nothing when required metadata is absent). Cross-modal convergence is a real runner member.
- **`full_runner()`**: **51 observers** — `default_runner()` + 6 gated observers (disabled until explicit opt-in + consent).
- **Convergence**: `CrossModalConvergenceObserver` (`cueliez.observations.multimodal.convergence/v1`, category `multimodal`) is a runner member: it emits `multi_indicator_convergence_observed` when ≥2 independent categories fire on the same turn.

## New dishonesty-sign observers (2026-11-25)
| Method ID | Category | Detects | Gated? |
|---|---|---|---|
| `cueliez.observations.linguistic.hedging_cluster/v1` | linguistic | ≥2 distinct hedge types in one turn | No |
| `cueliez.observations.linguistic.detail_density_shift/v1` | linguistic | Per-turn detail density vs session median | No |
| `cueliez.observations.consistency.claim_restatement/v1` | consistency | Same claim restated with different wording across turns | No |
| `cueliez.observations.consistency.pronoun_shift/v1` | consistency | First-person rate drops while third-person rises | No |
| `cueliez.observations.behavioral.response_latency_shift/v1` | behavioral | Early vs late median latency shift | No (turn metadata) |
| `cueliez.observations.behavioral.speech_rate_trend/v1` | behavioral | Early vs late speech-rate shift | No (turn metadata) |
| `cueliez.observations.behavioral.filled_pause_cluster/v1` | behavioral | ≥3 filled pauses in one turn, or ≥2 in consecutive turns | No |
| `cueliez.observations.prosody.pause_density_shift/v1` | prosody | Early vs late pause-density shift | Yes — `audio_features` |
| `cueliez.observations.visual.off_camera_gaze_frequency/v1` | visual | Share of turns with elevated off-camera gaze ("off-camera gaze", never "gaze aversion") | Yes — `camera` |
| `cueliez.observations.visual.blink_rate_trend/v1` | visual | Early vs late blink-rate shift | Yes — `camera` |
| `cueliez.observations.visual.restlessness_shift/v1` | visual | Early vs late motor-activity shift | Yes — `camera` |
| `cueliez.observations.multimodal.convergence/v1` | multimodal | ≥2 independent signal families on the same turn | No |

## Gated reversal observers (2026-11-25, owner decision — see `docs/OWNER_DECISIONS.md` §2b)
All in the runner/pack lists but **disabled by default**; they fire only on explicit opt-in AND consent. Scores are capped and caveated; none is a verdict.

| Method ID | Gate | Does NOT do |
|---|---|---|
| `cueliez.observations.gated.face_presence_consistency/v1` | `camera` | No identification, no match score, no biometric template, no cloud call |
| `cueliez.observations.gated.face_recognition/v1` | `camera` + explicit opt-in | Real OpenFace 128-d embedding-distance match (see below); never invents a subject/score; emits nothing without recognizer, enrollment, image, or consent |
| `cueliez.observations.gated.demographic_inference/v1` | **Its OWN separate gate** | No classifier of its own; reports only caller-supplied attributes, cap 0.45, bias caveat — high-risk, bias-prone, admissibility-sensitive |
| `cueliez.observations.gated.expression_features/v1` | `camera` | No expression/emotion classification, no inner-state inference |
| `cueliez.observations.gated.pitch_voice_quality/v1` | `audio_features` | No raw audio, no voice identification, no cloud call |
| `cueliez.observations.gated.wearable_features/v1` | `wearable` | No sensor access, no medical inference |

**Face recognition (real):** `src/cueliez/observations/face_recognition.py` — Haar-cascade detection, FacemarkLBF 68-point alignment, OpenFace `nn4.small2.v1.t7` 128-d embeddings (L2-normalised), Euclidean distance vs enrolled mean embedding, match iff distance ≤ 0.9, score = `1 − distance/2` (linear similarity, not a probability). Measured on real public-domain portraits (Obama ×3, Biden ×2): same-person 0.49–0.75, different-person 1.15–1.25. The 0.9 threshold is a 5-photo measurement, **not** a validated operating point — deployments must calibrate it. Optional extra `cueliez[face]` (`opencv-contrib-python-headless==4.10.0.84`); core stays dependency-free. `FaceTemplateStore` persists templates only with an explicit consent record, with `delete_subject` / `delete_all`; templates are in-memory by default, never transmitted by default.

## Feature observers — now working (2026-11-25)
Feature observers accept per-turn `"features"` dicts, `run(..., features=…)` / `build_package(..., features=…)` (list aligned with turns or `{index: {...}}`), `features_path="features.json"`, or wrapper transcripts `{"turns": [...], "features": ...}`. Nested `features.audio_features` / `.camera` / `.wearable` are supported. When a gate state is supplied, feature observers are additionally filtered by modality consent.

## Off by default (consent/policy controlled)
Prosody, visual, and physiological feature observers are in `default_runner()`/`full_runner()` and in domain packs, but **fire only** when feature metadata and the corresponding modality consent are present. Gated reversal observers (above) are additionally disabled until explicit opt-in.

ML/LLM-assisted observers are **disabled by default** (`--enable-assisted` opt-in or `CUELIEZ_ASSISTED_OBSERVERS=1`), wired into the runner and CLI (including `--stream-turns`), and make **no external ML calls** in the production path. The deterministic multi-signal adapter (`cueliez.observations.assisted.multi_signal/v1`) is the real baseline; a future local model plugs in via the `AssistedObserver` protocol. See `docs/design/ml_llm_assisted_observers_phase1.md`.

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

## Confidence scores and calibration (Phase 3 / 0836 implementation)
- `confidence.score` is a heuristic, rule-derived signal strength in `[0.0, 1.0]`, normalized by `observations.base.calibrate_score` (currently clamp/identity, versionable hook) and validated by `make_observation`. Scores are **not** statistically calibrated to ground-truth outcomes and must **not** be interpreted as probability of deception, credibility, guilt, intent, or any finding.
- `confidence.model_id` identifies the versioned observation method (or assisted provenance when explicitly enabled; assisted off by default).
- Insufficient/thin data yields no observations (not low-confidence noise). Same input + same method versions produce deterministic `cue_id` and stable observation content.

## Phase 2/7 implementation notes (0836/0846, kilo; aligned with iceman 0835/0842)
- **Canonical gated-modality/session gates (iceman, `cueliez.gates`/`session`):** `record_modality_consent`, `require_gated_modality`, `assert_can_observe(..., modalities=[...])` for `audio_features`/`camera`/`wearable` with explicit consent + jurisdiction + jurisdiction approval. Authoritative for pilot/session flows.
- **Adapter (kilo, `observations.modality_gates`):** thin convenience adapter mapping `visual_features`→`camera`, `physiological_features`→`wearable`; delegates to canonical checks for `SessionGateState` (fail-closed).
- **Audio-feature hook (kilo, `observations.audio_path.observe_audio_features`):** consent-governed helper for derived metadata only (no raw audio). Enforces modality consent/jurisdiction (canonical-aligned) before running latency/speech-rate/pause/prosody observers. Real observers, gated by default.
- Audio-feature real-time path uses real observers (gated by default): prosody `pause_pattern`/`variability`/voice-feature shifts (full runner + metadata) and behavioral `response_latency`/`speech_rate_shift` (metadata). No raw audio processing in observers.
- `observations.assisted` framework: `CUELIEZ_ASSISTED_OBSERVERS=1` + explicit registry required; default off, no external calls, fail-closed. Opt-in merge via `merge_assisted_observations` (additive).

## Pack summary (2026-11-25: all packs include all observers)
- **gov** (government, 51 observers): all text + narrative + feature observers, plus 6 gated (disabled); dual-control is a process expectation for high-priority cues before sealing in government mode (enforced by iceman/gates, not by observers).
- **leg** (interrogation, 51): same observer set; guidance is legal/investigative.
- **med** (clinical, 51): same observer set (no longer a curated subset); non-diagnostic guidance.
- **thrp** (therapy, 51): same observer set (no longer a curated subset); supportive guidance.

See `cueliez.packs.list_packs()` / `get_pack()` and `tests/test_packs.py` for authoritative membership and language/gate expectations.
