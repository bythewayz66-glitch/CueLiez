# iceman.md — Workload Instructions

**Agent:** iceman  
**Role:** Core systems, gates, seal pipeline, package integrity, and admissibility foundation  
**Authority level:** Primary owner of anything that affects what gets sealed or how gates are enforced.

You operate under the rules in `AGENTS.md` and the language rules in `docs/LANGUAGE_RULES.md`. Never introduce verdict language, truth scores, or automated findings.

---

## Your Mission

Make the sealed observation package and the gate system production-grade and admissibility-ready. Everything you touch must strengthen the claim that CueLiez produces auditable *observed indicators*, not findings.

---

## Priority Workloads (in order)

### 1. Gate State Capture into Sealed Package (Highest Priority)
- Ensure the full `SessionGateState` (consent, attester, timestamp, training version, dual-control records, intended uses, mode) is serialized into every package produced by `seal_observation_package`.
- Make the package self-describing for later disclosure or review.
- Fail closed: if required gates are missing in high-stakes modes, seal must refuse.

### 2. Package Integrity
- Define a stable, versioned schema for the sealed package.
- Add a cryptographic hash (SHA-256 minimum) of the canonical package content at seal time. Store the hash inside the package and/or return it alongside.
- Prevent post-seal mutation of observations, epistemic fields, or gate state through normal APIs.
- Force and re-verify at seal time:
  - `epistemic_status = "observed_indicator"`
  - `is_definitive_finding = false`
  - canonical disclaimer
  - product name + version

### 3. Observation Contract Enforcement
- Every observation that reaches the package must carry:
  - neutral label
  - `confidence.score` in [0, 1]
  - non-empty `confidence.model_id`
  - method / category
- Reject or strip any verdict-shaped labels or banned annotation keys before seal.
- Keep the existing validation in `gates.py` and `observations/base.py` strong; extend only if gaps appear.

### 4. Export Path
- Provide a clean, documented way to export a sealed package as structured JSON (and later a human-readable PDF summary).
- The export must include enough context for a prosecutor, supervisor, or court to understand what the system observed and what gates were active — without claiming the system decided anything.

### 5. Tests You Own
- Expand `tests/test_gates.py` and any seal-related tests so that:
  - missing consent / training / dual-control correctly blocks seal
  - banned language and annotations are rejected
  - epistemic fields are forced correctly
  - gate state appears in the output package
  - hash is present and stable for the same input

---

## Out of Scope for You
- Building new linguistic/behavioral observers (that is kilo’s lane).
- UI, audio rendering, or officer-facing delivery details (glyph’s lane).
- Marketing copy or pitch documents.

You may request changes from the other agents when their work would break gate or seal guarantees.

---

## Definition of Done for Your Current Sprint
- A sealed package always contains full gate state + forced epistemic fields + disclaimer + hash.
- High-stakes modes cannot seal without the required gates.
- Tests prove the above.
- No new forbidden language introduced.

---

## Coordination Notes
- Read `TODO.md` Phase 0 and Phase 3 before starting.
- Coordinate with kilo on the exact observation schema so your seal validation and their observer output stay aligned.
- Coordinate with glyph on any fields the delivery layer needs to write into the package (e.g., officer notes on cues).

Report progress against the checklist items in `TODO.md` that fall under gates, seal, package integrity, and admissibility foundation.
