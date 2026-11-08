# Note

**From:** orchestrator
**To:** all (iceman, kilo, glyph)
**Date:** 2026-11-08
**Topic:** Phase 7 — IMPLEMENT live Axon/RMS/CaseCracker connectors (owner demand)

## Message

Owner wants **live connectors** for Axon/RMS/CaseCracker implemented now (not docs-only). Implement real connector code with environment-based configuration (no hardcoded credentials), graceful offline behavior, and tests using mocked endpoints. Do not fabricate vendor APIs; document required env vars and expected payloads.

Per-agent notes:
- `2026-11-08_0854_orchestrator_to_iceman_phase7-live-connectors.md`
- `2026-11-08_0855_orchestrator_to_kilo_phase7-live-connectors.md`
- `2026-11-08_0856_orchestrator_to_glyph_phase7-live-connectors.md`

### Orchestrator (self) tasks
- Coordinate contracts/config; verify conformance.
- Update `TODO.md` only after agents confirm.
- Keep `agent_notes/` and `PROGRESS.md` current; do not push agents' active work.

### Constraints
- No hardcoded secrets; use env vars.
- Neutral wording only.
- Tests must not require live vendor access (mocked).

## Action required
- [ ] Read your individual note
- [ ] Execute in order; update PROGRESS.md per major item
- [ ] Reply via agent_notes for contract changes

## Reply needed
PROGRESS updates; notes for contract changes.