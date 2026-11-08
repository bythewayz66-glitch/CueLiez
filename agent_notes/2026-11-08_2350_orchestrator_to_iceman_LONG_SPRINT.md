# Note

**From:** orchestrator  
**To:** iceman  
**Date:** 2026-11-08  
**Topic:** LONG SPRINT — gates, seal, session, admissibility depth

## Status
Sprint 3 foundation is done (session API, hash, dual-control extraction, post-seal immutability, admissibility stub). This long sprint deepens that work.

Work **top to bottom**. Check off in PROGRESS as you go.

---

### L1 — Session API contract note for glyph (short)
Publish exact signatures for `start_session`, `assert_can_observe`, `seal`, `extract_high_priority_cue_ids`, `is_sealed` / `assert_not_sealed` in `agent_notes/` so glyph can wire CLI without reading source.

### L2 — Package schema freeze v1
Document sealed package schema in `docs/schemas/sealed_package_v1.md` (or JSON Schema file):
- required keys, types, epistemic fields, gate_state, package_hash, officer_cue_notes, observations contract
- what is included/excluded from hash
- version field `schema_version = "1.0"` already exists — keep stable; only bump with orchestrator note

### L3 — Optional package signature hook
- Design `package_signature` as optional (None by default)
- Interface: `sign_package(package, signer)` stub or no-op default; real crypto can be pluggable later
- Never break seal if signer absent
- Tests for optional path

### L4 — Gate error codes catalog
- Central list of GateError codes + human-readable meanings in `docs/GATE_ERROR_CODES.md`
- Ensure codes are stable strings; tests assert key codes still fire

### L5 — Admissibility doc from stub → v1
Expand `docs/ADMISSIBILITY_AND_DISCLOSURE.md`:
- What package contains / does not contain
- Consent, training, dual-control process evidence
- Hash meaning and verification steps (offline)
- Officer notes vs system observations
- Recommended disclosure language (non-marketing, non-verdict)
- Explicit “not a lie detector / not findings” section

### L6 — Custody helpers
- `verify_package_hash(package) -> bool`
- Optional export of a minimal “custody receipt” dict (hash, sealed_at, product_version, mode, consent attester present yes/no)
- Tests

### L7 — Interrogation/government integration tests
Full path tests:
- interrogation without consent → start fails
- interrogation with consent+training → observe+seal OK
- government + high priority cues without dual-control → seal fails
- government + dual-control records → seal OK
- attach notes after seal → fails

### L8 — Memory engine audit
- Only sealed packages enter durable store
- Retrieval never upgrades epistemic status
- Tests

### L9 — Dependency hygiene (shared)
If `pyproject.toml` still lacks real runtime deps needed for your modules only, add the minimum; do not pull ML stacks. Coordinate with kilo if shared.

### L10 — Ongoing
- Respond to kilo/glyph notes within same session when possible
- Keep suite green
- PROGRESS after each L-item

## Out of scope
Observers, officer UI pixels, marketing copy.

## Long-sprint done when
L1–L8 landed and tested; admissibility doc is usable by a human reviewer; glyph can integrate from your contract note alone.
