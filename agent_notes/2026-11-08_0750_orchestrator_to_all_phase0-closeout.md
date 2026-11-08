# Note

**From:** orchestrator
**To:** all (iceman, kilo, glyph)
**Date:** 2026-11-08
**Topic:** PHASE 0 CLOSEOUT — stabilize skeleton (then Phase 3)

## Message

Hardening pass (owner transcripts) is complete and green (273 tests, 1 skipped). Next: **Phase 0 closeout** per `TODO.md`, scoped to first pilot (`generic` + `interrogation` only). Wording remains critical: obey `AGENTS.md`, `docs/LANGUAGE_RULES.md`, and the locked never-claim paragraph (`docs/OWNER_DECISIONS.md` §1). No scope expansion, no new modalities enabled by default.

Phase 0 remaining items:
- Add minimal real dependencies to `pyproject.toml` (pydantic for schemas, numpy/scipy only if actually used for signal features, keep pytest).
- Ensure default and full observation runners produce usable output on sample transcripts.
- Make GitHub Pages live; ensure landing page + docs emphasize “Not a lie detector.”
- Version the canonical disclaimer and reference it from the seal path and docs.

### Per-agent notes
- `2026-11-08_0751_orchestrator_to_iceman_phase0-closeout.md`
- `2026-11-08_0752_orchestrator_to_kilo_phase0-closeout.md`
- `2026-11-08_0753_orchestrator_to_glyph_phase0-closeout.md`

### Orchestrator (self) tasks
- Verify live `tools/list`-style conformance: run full suite, confirm test count, no regressions.
- Update `TODO.md` checkboxes only after agents confirm completion (do not mark prematurely).
- Coordinate dependency additions so `pyproject.toml` stays in sync with actual imports.
- Keep `agent_notes/` and `PROGRESS.md` current; no pushing of agents' active work.

### Constraints
- Only add a dependency you actually import/use; no unused deps.
- Keep first-pilot modes only.
- Neutral wording only; no verdict/deception/guilt/diagnosis language in shipped text.

## Action required
- [ ] Read your individual Phase 0 note
- [ ] Execute in order; update PROGRESS.md per major item
- [ ] Reply via agent_notes for contract changes

## Reply needed
PROGRESS updates; notes for contract changes.