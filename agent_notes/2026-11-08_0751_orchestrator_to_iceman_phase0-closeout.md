# Note

**From:** orchestrator
**To:** iceman
**Date:** 2026-11-08
**Topic:** PHASE 0 CLOSEOUT — versioned disclaimer + seal reference

## Message

Phase 0 closeout kickoff. Your scope: version the canonical disclaimer and reference it from the seal path and docs. Dependencies: add pydantic only if you use it for schema validation; otherwise leave deps unchanged. Coordinate via note if you add a dependency.

### Tasks (in order)
1. **Versioned disclaimer** — Add a canonical disclaimer constant with a version identifier (e.g., `DISCLAIMER_VERSION = "v1"` or a hash) in `cueliez.compliance.disclaimers` (or gates). Ensure the seal path embeds both the disclaimer text and its version in every sealed package.
2. **Seal path reference** — `seal_observation_package` (and `MemoryEngine.seal_package`) must use the versioned disclaimer constant (no duplicated string literals in seal code). Update docs/schema to reference the version.
3. **Tests** — Add tests verifying the sealed package contains the canonical disclaimer text and version, and that altering the disclaimer constant changes the version (if hash-based). Keep epistemic fields forced.
4. **Docs** — Update `docs/ADMISSIBILITY_AND_DISCLOSURE.md` and `docs/schemas/sealed_package_v1.md` to mention disclaimer version and verification.
5. **Dependency** — If you introduce pydantic for schema validation, add it to `pyproject.toml` dependencies and import it in code; otherwise leave deps empty. Post a note if you add it.

### Constraints
- First-pilot modes only (`generic`, `interrogation`).
- No new modalities enabled by default.
- Neutral wording only; disclaimer must match never-claim paragraph (`OWNER_DECISIONS.md` §1).
- Run full suite before reporting.

### Deliverables
- Code + tests + docs committed by you.
- PROGRESS.md iceman section updated.
- agent_note for dependency or schema changes.

## Action required
- [ ] Execute tasks 1–5
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for dependency/schema changes.