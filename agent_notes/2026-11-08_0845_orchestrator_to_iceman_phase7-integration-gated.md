# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** Phase 7 — Integration & Gated Modalities (iceman scope)

## Message

Phase 7 kickoff. Your scope: integration readiness and gate hardening for gated modalities. No live Axon/RMS integration required unless a partner supplies transcript export.

### Tasks (in order)
1. **Transcript ingest contract** — Document and (if useful) implement a stable ingest path for transcript JSON into sealed packages (attach as original artifacts). Add tests.
2. **Gate hardening for gated modalities** — Ensure consent + jurisdiction checks are enforced before enabling audio feature extraction or camera/wearable input; add `GateError` codes and tests.
3. **Government mode external pilot** — Keep dual-control enforced; document requirements; tests.
4. **Clinical/therapy packs** — Keep present in code but out of pilot messaging; ensure gate rules apply.
5. **Tests/docs** — Keep suite green; update docs.

### Constraints
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–5
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.