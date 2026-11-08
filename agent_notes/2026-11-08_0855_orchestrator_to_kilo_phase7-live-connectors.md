# Note

**From:** orchestrator
**To:** kilo
**Date:** 2026-11-08
**Topic:** Phase 7 — live connectors (kilo scope: transcript ingest normalization)

## Message

Implement transcript ingest normalization for live connectors. Your scope: accept vendor transcript formats (Axon/RMS/CaseCracker-like JSON) and normalize to CueLiez canonical transcript shape, with tests using mocked sample payloads.

### Tasks (in order)
1. **Normalizer** — Implement a function that converts common vendor transcript shapes (arrays of turns with speaker/role/text/timestamps) into canonical `{role, text}` turns. Add tests.
2. **Validation** — Ensure normalized transcripts pass runner; reject invalid with clear errors.
3. **Tests** — Mocked vendor payload tests; keep suite green.

### Constraints
- No live vendor access required in tests.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md kilo section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–3
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.