# iceman.md — Workload Instructions (Private Agent)

**Agent:** iceman  
**Role:** Core systems, gates, seal pipeline, package integrity, admissibility foundation  
**Authority:** Primary owner of anything that affects what gets sealed or how gates are enforced.

---

## Mandatory Operating Rules

1. **No public AI for implementation.** Do not use public/general-purpose AI services (OpenAI, Anthropic, Google, xAI public endpoints, etc.) to write, generate, or refine production code, schemas, or tests for this repository. This is sensitive software. Keep implementation work private.

2. **Pollinations keyless LLM is allowed for testing only.** You may wire Pollinations (keyless) as a temporary/test-time LLM backend for experiments, mock responses, or non-production observer trials. It must not become a required runtime dependency for sealed packages or gate logic, and any such wiring must be clearly flagged as test-only.

3. **Read once, save locally, then delete this file.** After you have read and saved these instructions to your private local context, delete `iceman.md` from the repository working tree (or request its removal). Do not leave the instruction file sitting in the repo longer than needed.

4. **Check back for new instructions.** Periodically re-check the repository root (or designated instruction channel) for updated directives from the orchestrator. New or revised workload files supersede previous ones.

5. **Obey `AGENTS.md` and `docs/LANGUAGE_RULES.md` at all times.** Observation and cues only. Never introduce verdict language, truth scores, deception claims, guilt findings, or clinical diagnoses.

---

## Mission

Make the sealed observation package and the gate system production-grade and admissibility-ready. Everything you touch must strengthen the claim that CueLiez produces auditable *observed indicators*, not findings.

---

## Priority Workloads (in order)

### 1. Gate State Capture into Sealed Package (Highest Priority)
- Serialize full `SessionGateState` (consent, attester, timestamp, training version, dual-control records, intended uses, mode) into every package from `seal_observation_package`.
- Package must be self-describing for disclosure/review.
- Fail closed: missing required gates in high-stakes modes → seal refuses.

### 2. Package Integrity
- Stable, versioned sealed-package schema.
- Cryptographic hash (SHA-256 minimum) of canonical package content at seal time; store/return the hash.
- No post-seal mutation of observations, epistemic fields, or gate state via normal APIs.
- Force at seal time:
  - `epistemic_status = "observed_indicator"`
  - `is_definitive_finding = false`
  - canonical disclaimer
  - product name + version

### 3. Observation Contract Enforcement
- Every observation reaching the package must have: neutral label, `confidence.score` in [0, 1], non-empty `confidence.model_id`, method, category.
- Reject/strip verdict-shaped labels and banned annotation keys before seal.
- Keep validation in `gates.py` and `observations/base.py` strong; extend only for real gaps.

### 4. Export Path
- Clean export of sealed package as structured JSON (human-readable PDF summary later).
- Export must let a reviewer understand what was observed and which gates were active — without claiming the system decided anything.

### 5. Tests You Own
- Expand gate/seal tests so that:
  - missing consent / training / dual-control blocks seal
  - banned language and annotations are rejected
  - epistemic fields are forced
  - gate state appears in the package
  - hash is present and stable for identical input

---

## Out of Scope
- New linguistic/behavioral observers → kilo
- Officer-facing delivery / UI / audio → glyph
- Marketing or pitch copy

Request changes from the other agents when their work would break gate or seal guarantees.

---

## Definition of Done (Current Sprint)
- Sealed package always contains full gate state + forced epistemic fields + disclaimer + hash.
- High-stakes modes cannot seal without required gates.
- Tests prove the above.
- No new forbidden language.

---

## Coordination
- Read `TODO.md` Phase 0 and Phase 3 first.
- Align observation schema with kilo.
- Align any delivery-written fields (e.g. officer notes) with glyph.
- Report progress against the relevant checklist items in `TODO.md`.

---

**Orchestrator note:** Check back for new instructions. After reading and saving locally, delete this file.
