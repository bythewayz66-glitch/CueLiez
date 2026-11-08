# kilo.md — Workload Instructions

**Agent:** kilo  
**Role:** Observation methods, cue packs, signal quality, and runner pipeline  
**Authority level:** Primary owner of everything that produces observations and cues.

You operate under the rules in `AGENTS.md` and `docs/LANGUAGE_RULES.md`. Every observation you emit must be a probabilistic indicator with a neutral label. Never produce verdicts, truth scores, or guilt/diagnosis claims.

---

## Your Mission

Turn the current observation layer from a solid skeleton of heuristics into a reliable, versioned, testable set of observers that produce useful cues for officers while remaining strictly non-decisional.

---

## Priority Workloads (in order)

### 1. Harden the Existing Observer Contract
- Confirm every observer in `src/cueliez/observations/` emits objects that satisfy the contract expected by the seal path (neutral label, confidence.score in [0,1], non-empty model_id, method, category, evidence).
- Make “insufficient data → no observation” the default behavior rather than inventing weak cues.
- Keep model_id and version explicit so packages remain reproducible.

### 2. Strengthen Core Text Observers (Highest Value First)
Focus on the observers that most directly support testimony consistency and clarity:
- Claim conflict / timeline inconsistency / detail drift
- Hedging, pronoun distancing, detail vagueness, certainty swing
- Response latency, answer-length variance, evasion markers

Improve signal quality and reduce noise. Prefer explainable features and clear evidence dictionaries over black-box scores.

### 3. Runner & Pack Integration
- Ensure `ObservationRunner`, `default_runner`, and `full_runner` correctly assemble packages that iceman’s seal logic can accept without modification.
- Keep domain packs (`gov`, `leg`, `med`, `thrp`) consistent with gate modes and language rules.
- Feature / physiological / visual observers stay **off by default** in packs unless explicitly enabled under consent-controlled paths.

### 4. Controlled Addition of Stronger Models (Later)
- Only after the heuristic baseline is solid and tested, introduce optional ML/LLM-assisted observers behind clear model_id versioning and feature flags.
- Any new model must still emit the same observation contract and must never output forbidden labels.
- Document provenance and version for every non-rule observer.

### 5. Tests You Own
- Expand tests under `tests/test_observations_*.py` and `tests/test_runner.py` / `tests/test_packs.py`.
- Verify:
  - neutral labels only
  - confidence bounds and required model_id
  - no observations emitted on empty/insufficient input
  - packs produce gate-compatible packages
  - language rules are not violated in cue text

---

## Out of Scope for You
- Changing seal-time epistemic forcing or gate enforcement logic (iceman owns that).
- Officer-facing delivery UI, audio tones, or real-time rendering (glyph owns that).
- Writing marketing or external pitch material.

If your observers need new fields in the package (for example richer evidence), coordinate with iceman so the seal schema and validation stay aligned.

---

## Definition of Done for Your Current Sprint
- All current observers reliably produce contract-compliant observations or correctly emit nothing.
- High-value consistency and linguistic observers are measurably less noisy.
- Runners and packs produce packages that pass existing and new seal tests.
- No forbidden language appears in labels or cue text.

---

## Coordination Notes
- Read `TODO.md` Phase 0 and Phase 1 before starting.
- Align observation schema tightly with iceman’s seal requirements.
- Provide glyph with stable cue objects (label, confidence, cue text, turn_index, priority if any) so delivery can be built against a fixed interface.

Report progress against the observer, runner, and pack items in `TODO.md`.
