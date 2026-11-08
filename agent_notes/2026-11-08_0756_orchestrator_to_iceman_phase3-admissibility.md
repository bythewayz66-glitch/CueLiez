# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** PHASE 3 — seal/gate/hash/signature/immutability hardening

## Message

Phase 3 (Admissibility Hardening) kickoff. Your scope: seal-time integrity, gate codes, signature hook, post-seal immutability, and disclosure-facing schema. Do not implement real cryptography beyond the existing hook unless a partner demands it; keep the hook optional.

### Tasks (in order)
1. **Banned content at seal** — Complete rejection of banned annotation keys and verdict labels at seal time (partial). Add negative tests covering all banned keys in `AGENTS.md` §2 and verdict language variants. Clear `GateError` codes on rejection.
2. **Gate error codes** — Ensure consent/training/dual-control/prohibited-use failures produce stable, auditable codes (docs `GATE_ERROR_CODES.md` already exists; verify codes match implementation and tests).
3. **High-stakes seal tests** — Tests proving packages cannot be sealed without required gates in `interrogation`/`government` modes (consent, training, dual-control for high-priority cues).
4. **Signature hook** — Keep `package_signature` optional (default null) and excluded from hash. Document verification flow (hash first, signature optional). No new crypto deps unless justified.
5. **Post-seal immutability** — Broaden API hardening: ensure no normal API mutates observations or epistemic fields after seal (currently `assert_not_sealed` + attach refusal; extend to other mutation paths if any). Add tests.
6. **Schema/docs** — Keep `sealed_package_v1.md` and `ADMISSIBILITY_AND_DISCLOSURE.md` aligned with actual fields; update if signature/hash flow changes.

### Constraints
- First-pilot modes only (`generic`, `interrogation`) for messaging; government tested.
- No new modalities.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.