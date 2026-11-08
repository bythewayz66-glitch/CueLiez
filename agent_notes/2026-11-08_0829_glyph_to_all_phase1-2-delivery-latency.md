# Note

**From:** glyph  
**To:** all (orchestrator, kilo, iceman)  
**Date:** 2026-11-08  
**Topic:** Phase 1+2 (0828) — delivery provenance display + local latency measurement (no contract changes)

## Message
Completed glyph scope for 0828: hardened officer-facing delivery surfaces (turn-linked/glanceable, acknowledge/dismiss/note, subject not shown by default) and added neutral **method/model provenance** display alongside confidence scores in CLI text, officer HTML, onscreen HTML, and Markdown/HTML exports (observation-only; no accuracy claims). Officer note capture/attach-before-seal/export path remains intact (tests green).

Local 2026-11-08 reference (owner fixtures, default text path, `--no-seal`, environment-specific): in-process observe+cues+render ~2–5 ms; end-to-end CLI subprocess ~275–390 ms. Not a guarantee; meets <1–2 s text target in this check.

**No API/contract changes.** Rendered output includes an added provenance field/column; consumers parsing exact text/table shapes may need to tolerate the addition.

## Action required
- [ ] None.

## Reply needed
No.
