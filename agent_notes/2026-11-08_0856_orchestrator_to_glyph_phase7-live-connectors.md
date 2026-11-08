# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** Phase 7 — live connectors (glyph scope: connector UI/CLI/export)

## Message

Implement live connector UI/CLI/export support. Your scope: CLI commands to push/pull sealed packages to/from a configured endpoint, with env-based config, offline graceful behavior, and tests using mocked endpoints. No hardcoded credentials.

### Tasks (in order)
1. **CLI connectors** — Add CLI options (e.g., `--push-endpoint`, `--pull-id`) that use env-based config; implement HTTP push/pull with timeouts and retries; graceful offline errors.
2. **Export integration** — Ensure evidence-bundle export can be triggered after a successful push; document.
3. **Tests** — Mocked endpoint tests; keep suite green.

### Constraints
- No live vendor access required in tests.
- Neutral wording only.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md glyph section updated.
- agent_note for contract changes.

## Action required
- [ ] Execute tasks 1–3
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.