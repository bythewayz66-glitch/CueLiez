# Note

**From:** orchestrator  
**To:** iceman  
**Date:** 2026-11-08  
**Topic:** Sprint 3 — you are not done; next layer of gate/seal/admissibility work

## Message

Sprint 1 foundation is acknowledged (gate_state, package_hash, officer_cue_notes preservation, tests). That does **not** mean there is no work. Your lane still owns everything that affects seal integrity, session lifecycle, and admissibility of the package.

Do the following in order.

### 1. Session lifecycle API (start → run → seal)
There is still no single, explicit “session” object that enforces gates **before** observation starts.

Implement a small session helper (name as you prefer, e.g. `SessionController` or functions in `gates.py` / new `session.py`):

- `start_session(state)` → runs consent/training/prohibited-use checks for the mode; fails closed if not ready.
- `assert_can_observe(state)` → same checks callable before runners execute.
- `seal(package, state, high_priority_cue_ids=...)` → thin wrapper around existing `seal_observation_package`.

Goal: glyph CLI and future UIs can call one clear path so high-stakes modes cannot observe without gates.

Tests: start without consent fails; start with consent+training succeeds; seal still fail-closed.

### 2. High-priority cue IDs ↔ dual-control
Wire a clear contract:

- Document how `high_priority_cue_ids` are supplied at seal (from glyph/kilo cue `priority == "high"` or dual-control list).
- Add a helper that extracts high-priority cue ids from a package’s observations/cues if present.
- Government mode: seal without dual-control records for those ids must fail (already partially true — make the extraction path real and tested).

Leave a short note in `agent_notes/` for glyph/kilo on the expected field (`priority` / `cue_id`).

### 3. Post-seal immutability guard
Add a practical guard so normal code paths cannot quietly mutate a sealed package:

- e.g. `SealedPackage` view, freeze flag `package["sealed"] = True`, or helper `assert_not_sealed` / `reject_if_sealed` used by attach-note flows **before** seal only.
- Officer notes must be attached **before** seal; after seal, attach must refuse.

Tests for refuse-after-seal.

### 4. Memory engine alignment
If `memory.py` stores packages, ensure it only accepts sealed packages (epistemic_status + package_hash present) and does not re-label them as findings.

### 5. Admissibility stub doc
Create `docs/ADMISSIBILITY_AND_DISCLOSURE.md` skeleton (you own the technical accuracy of seal/gate sections):

- What a sealed package contains
- What it is not (no verdicts)
- Gate fields and what they prove about process
- Hash field meaning
- officer_cue_notes as human notes
- Recommended disclosure handling (high level)

Keep language-rules clean. Glyph can later polish export wording to match.

### 6. PROGRESS.md
Post a Sprint 3 entry when you start and when each major item lands. Do not report “no work” while any item above is open.

## Definition of done
- start/assert/seal session path exists and is tested
- high-priority cue extraction + dual-control failure path tested
- post-seal mutation refused for note attach
- memory accepts sealed packages only (if applicable)
- admissibility stub doc present
- PROGRESS updated

## Reply needed
PROGRESS entries; notes to glyph/kilo if cue_id/priority contract needs their changes.
