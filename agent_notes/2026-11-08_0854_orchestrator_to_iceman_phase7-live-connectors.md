# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** Phase 7 — live connectors (iceman scope: seal/ingest contract)

## Message

Implement live connector support from the seal/ingest side. Your scope: ensure sealed packages are attachable as original artifacts via a documented ingest contract, and that connector failures produce auditable GateError codes. No hardcoded credentials.

### Tasks (in order)
1. **Ingest contract** — Define and implement a stable ingest endpoint/function that accepts a sealed package and validates hash/epistemic fields. Add tests.
2. **GateError codes** — Add codes for connector/ingest failures (auth, network, validation).
3. **Tests** — Mocked ingest tests; keep suite green.

### Constraints
- No live vendor access required in tests.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–3
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.