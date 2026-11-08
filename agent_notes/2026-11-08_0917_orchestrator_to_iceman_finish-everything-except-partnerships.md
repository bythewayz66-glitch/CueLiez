# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** Finish everything (except partnerships) — iceman scope

## Message

Finish all remaining in-progress/open work. Your scope: dependencies, on-prem/CJIS readiness, data retention/access controls, RMS attachment, government/clinical pilots, Phase 8 gate updates, real-time audio hooks (gate side), gated modality enablement (gate side).

### Tasks (in order)
1. **Dependencies** — Add pydantic (or other) only if used; otherwise document decision. Update `pyproject.toml` if added.
2. **On-prem/CJIS readiness** — Document deployment posture, data location, access controls, operational readiness (not just design notes).
3. **Data retention & access controls** — Document retention periods, access controls, custody handling.
4. **RMS attachment** — Ensure sealed packages attach as original artifacts; document ingest expectations; tests.
5. **Government/clinical external pilots** — Document dual-control requirements and clinical/therapy pack boundaries; keep out of pilot messaging unless scoped.
6. **Real-time audio hooks (gate side)** — Ensure consent + jurisdiction checks enforced before audio feature extraction; add GateError codes/tests.
7. **Gated modality enablement (Phase 8 gate side)** — Update consent/training gates to reflect new defaults when enabled; re-verify admissibility checklist.
8. **Tests/docs** — Keep suite green; update docs.

### Constraints
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–8
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.