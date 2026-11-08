# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** PHASE 3 — export/disclosure wording, PDF, disclosure guide

## Message

Phase 3 (Admissibility Hardening) kickoff. Your scope: export/delivery wording, disclosure-facing docs, and human-judgment preservation in UI/exports.

### Tasks (in order)
1. **Language audit (delivery/export)** — Audit CLI stdout, onscreen renderer, MD/HTML exports, and site pages for forbidden terms; ensure disclaimer first and observation-only framing. Extend `test_site_language.py`/`test_cli.py` if useful.
2. **Durable export** — If feasible, add print/PDF-friendly output (HTML is already print-friendly; document how to print-to-PDF). Do not add heavy deps without need; note if a real PDF library is added.
3. **Disclosure guide** — Keep `docs/ADMISSIBILITY_AND_DISCLOSURE.md` aligned with iceman schema/hash flow; ensure it explains what is/isn’t in the package, gate state, officer notes vs observations. No stronger claims than never-claim paragraph.
4. **Human judgment separation** — Ensure exports clearly separate “system-observed cues” from “officer notes (human)” and never imply automated findings. (Already mostly done; verify after iceman schema changes.)
5. **TODO accuracy** — Update glyph-owned checkboxes as items complete.

### Constraints
- First-pilot modes only in demo paths.
- Neutral wording only.
- No fabricated deployment status.

### Deliverables
- Docs/tests/UI changes committed by you.
- PROGRESS.md glyph section updated.
- agent_note for wording/contract changes.

## Action required
- [ ] Execute tasks 1–5
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for wording/contract changes.