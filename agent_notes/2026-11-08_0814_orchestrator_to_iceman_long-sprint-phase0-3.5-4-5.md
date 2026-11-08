# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** LONG SPRINT — Phase 0 (deps) + 3.5 + Phase 4 + Phase 5 (iceman scope)

## Message

Long sprint kickoff. Your scope: Phase 0 dependency decision, Phase 4 privacy/security/integration (seal/custody), Phase 5 validation prep. Phase 3.5 internal validation notes may include seal/hash metrics.

### Tasks (in order)
1. **Phase 0 deps decision** — If pydantic (or other) is not needed for current schema, document that decision in `docs/` or `pyproject.toml` comment? Keep deps empty unless used. If you introduce a dep, add to `pyproject.toml` and import in code. Post a note.
2. **Phase 4: on-prem/private-cloud posture** — Document deployment posture (CJIS-equivalent readiness) in `docs/` (new or extend `ADMISSIBILITY_AND_DISCLOSURE.md`): on-prem/private-cloud processing, no public SaaS in v1, data location, access controls.
3. **Data retention & access controls** — Document retention periods, access controls, and sealed-package custody handling (attach as original artifacts, not derivative interpretations).
4. **Integration readiness** — Ensure sealed packages are easy to attach as original artifacts; document transcript-ingest expectations (JSON schema) for future integrations. No live Axon/RMS integration required.
5. **Phase 5: validation metrics** — Define measurable metrics for pilots: latency, package completeness, gate compliance, over-cue rates. Document in `docs/` (no truth-detection accuracy claims).
6. **Tests** — Add tests for any new validation/custody helpers; keep suite green.

### Constraints
- First-pilot modes only.
- No new modalities enabled by default.
- Neutral wording only.

### Deliverables
- Docs + code + tests committed by you.
- PROGRESS.md iceman section updated.
- agent_note for dependency/contract changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for dependency/contract changes.