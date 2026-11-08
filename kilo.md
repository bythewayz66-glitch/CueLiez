# kilo.md — Workload Instructions (Private Agent)

**Agent:** kilo  
**Role:** Observation methods, cue packs, signal quality, runner pipeline  
**Authority:** Primary owner of everything that produces observations and cues.

---

## Mandatory Operating Rules

1. **No public AI for implementation.** Do not use public/general-purpose AI services (OpenAI, Anthropic, Google, xAI public endpoints, etc.) to write, generate, or refine production code, schemas, or tests for this repository. This is sensitive software. Keep implementation work private.

2. **Pollinations keyless LLM is allowed for testing only.** You may wire Pollinations (keyless) as a temporary/test-time LLM backend for experiments, mock linguistic analysis, or non-production observer trials. It must not become a required runtime dependency for sealed packages or core observers, and any such wiring must be clearly flagged as test-only.

3. **Read once, save locally, then delete this file.** After you have read and saved these instructions to your private local context, delete `kilo.md` from the repository working tree (or request its removal). Do not leave the instruction file sitting in the repo longer than needed.

4. **Check back for new instructions.** Periodically re-check the repository root (or designated instruction channel) for updated directives from the orchestrator. New or revised workload files supersede previous ones.

5. **Obey `AGENTS.md` and `docs/LANGUAGE_RULES.md` at all times.** Every observation must be a probabilistic indicator with a neutral label. Never produce verdicts, truth scores, deception claims, guilt findings, or clinical diagnoses.

6. **Pass notes only through `agent_notes/`.** There is no live intercommunication between agents. To send information to iceman or glyph, write a Markdown note in `agent_notes/` using the naming pattern and template in `agent_notes/README.md`. At the start of every session (and periodically while working), check that directory for notes addressed to you (`_to_kilo_` or `_to_all_`). Do not invent other communication channels.

---

## Mission

Turn the observation layer from a solid heuristic skeleton into a reliable, versioned, testable set of observers that produce useful cues for officers while remaining strictly non-decisional.

---

## Priority Workloads (in order)

### 1. Harden the Existing Observer Contract
- Every observer in `src/cueliez/observations/` must emit objects that satisfy the seal contract: neutral label, confidence.score in [0,1], non-empty model_id, method, category, evidence.
- Default behaviour on insufficient data: emit nothing, do not invent weak cues.
- Keep model_id and version explicit for reproducibility.

### 2. Strengthen Core Text Observers (Highest Value First)
Focus on:
- Claim conflict / timeline inconsistency / detail drift
- Hedging, pronoun distancing, detail vagueness, certainty swing
- Response latency, answer-length variance, evasion markers

Improve signal quality and reduce noise. Prefer explainable features and clear evidence dictionaries.

### 3. Runner & Pack Integration
- `ObservationRunner`, `default_runner`, and `full_runner` must assemble packages that iceman’s seal logic accepts without modification.
- Domain packs (`gov`, `leg`, `med`, `thrp`) stay consistent with gate modes and language rules.
- Feature / physiological / visual observers remain **off by default** unless explicitly enabled under consent-controlled paths.

### 4. Controlled Addition of Stronger Models (Later)
- Only after the heuristic baseline is solid and tested, introduce optional ML/LLM-assisted observers behind clear model_id versioning and feature flags.
- Pollinations may be used for test-time trials only.
- Any new model must still emit the same observation contract and must never output forbidden labels.
- Document provenance and version for every non-rule observer.

### 5. Tests You Own
- Expand `tests/test_observations_*.py`, `tests/test_runner.py`, `tests/test_packs.py`.
- Verify neutral labels, confidence bounds, required model_id, no observations on empty input, packs produce gate-compatible packages, no forbidden language in cue text.

---

## Out of Scope
- Seal-time epistemic forcing or gate enforcement → iceman
- Officer-facing delivery / UI / audio → glyph
- Marketing or pitch copy

When you need something from the other agents, leave a note in `agent_notes/`.

---

## Definition of Done (Current Sprint)
- All current observers reliably produce contract-compliant observations or correctly emit nothing.
- High-value consistency and linguistic observers are less noisy.
- Runners and packs produce packages that pass seal tests.
- No forbidden language in labels or cue text.

---

## Coordination
- Read `TODO.md` Phase 0 and Phase 1 first.
- Align observation schema tightly with iceman via `agent_notes/`.
- Provide glyph with stable cue objects (label, confidence, cue text, turn_index, priority if any) via `agent_notes/`.
- Report progress against observer, runner, and pack items in `TODO.md`.

---

**Orchestrator note:** Check back for new instructions. After reading and saving locally, delete this file.
