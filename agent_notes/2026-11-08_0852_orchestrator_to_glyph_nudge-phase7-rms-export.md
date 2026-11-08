# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** NUDGE — Phase 7 item 2: implement full RMS/case/evidence export (not docs-only)

## Message

Your Phase 7 report item (2) “RMS/case/evidence export (docs, no live integration)” is documentation only. The owner wants a **full implementation**, not just docs.

Please implement a real, working export path that writes a sealed package as an original artifact into a case/evidence-style folder structure, e.g.:
- a CLI option (e.g., `--export-evidence-dir`) that creates a deterministic folder containing `sealed_package.json`, `package_hash.txt`, and a human-readable summary, plus a manifest/index file listing artifacts and hashes;
- optional copy of officer notes and source transcript as separate immutable files;
- verification step that re-checks `package_hash` after writing;
- tests covering creation, hash verification, and no forbidden terms.

Do not add a live Axon/CaseCracker/RMS network connector unless a partner supplies credentials; a local, reproducible evidence-bundle export is acceptable as “full implementation.” No stubs/placeholders. Keep wording neutral and tests green. Update PROGRESS.md with the outcome.

### Action required
- [ ] Implement real evidence-bundle export (not docs-only)
- [ ] Add tests
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
Yes — PROGRESS update + note on implementation.