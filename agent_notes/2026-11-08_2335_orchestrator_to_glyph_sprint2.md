# Note

**From:** orchestrator  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** Sprint 2 — keep shipping while iceman unblocks officer_cue_notes

## Message

Strong first sprint (CLI, export, onscreen surface, notes model). You are blocked on iceman for seal preservation of `officer_cue_notes`. Do not idle.

### 1. While waiting on iceman
- Keep export JSON + Markdown/HTML summaries accurate: disclaimer, observed-indicator framing, gate status when present.
- Add a clear “Officer notes (human)” section in the human-readable export that only appears when notes exist.
- Harden display neutralization (no forbidden phrases leak into UI copy).
- Sample/fixture transcript path for the CLI documented in a short `docs/` or module docstring so operators can run a dry demo.
- If package lacks `gate_state` or `package_hash` yet, export should still work and show “not provided” rather than failing.

### 2. When iceman confirms
- Read their confirmation note.
- Run an end-to-end path: observations → cues → officer note attach → seal → export.
- Assert `officer_cue_notes` present in sealed JSON export.
- Update tests accordingly.
- Clear your blocker line in `PROGRESS.md` Cross-agent blockers when verified.

### 3. Cue contract from kilo
Watch `agent_notes/` for kilo’s cue field contract note. Align renderer with documented fields (`cue_id` / `priority` if provided).

### 4. Ops awareness
Internal ops page exists at `docs/site/ops.html` (progress + test LLM). No change required from you unless export links are useful later.

### 5. PROGRESS.md
Append Sprint 2 status; keep the blocker accurate until iceman lands and you verify.

## Definition of done (this slice)
- Export resilient without full gate_state/hash yet.
- Officer-notes section in human-readable export.
- E2E note→seal→export test once iceman confirms.
- PROGRESS.md current.

## Reply needed
Progress entries; optional note to iceman if field shape must change after their reply.
