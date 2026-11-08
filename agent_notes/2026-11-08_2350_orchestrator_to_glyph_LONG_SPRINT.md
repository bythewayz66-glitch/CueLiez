# Note

**From:** orchestrator  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** LONG SPRINT — operator path, export, dual-control handoff, demo

## Status
CLI, export, onscreen surface, officer notes, kilo contract alignment are in. Finish open Sprint 3 items, then continue this list.

Work **top to bottom**. PROGRESS after each major item.

---

### L1 — Wire CLI to iceman session API
Use `start_session` / `assert_can_observe` / `seal` from iceman’s contract note:

- `--mode generic|interrogation|government|clinical|therapy`
- Non-generic: `--consent-attester`, `--training-version` (and any required flags); fail closed with clear messages
- Notes attach only before seal

### L2 — High-priority dual-control handoff
- List high-priority `cue_id`s in CLI (`--list-high-priority` or always print summary)
- Onscreen: visual distinction for high priority (still non-accusatory copy)
- Export: list high-priority ids under process section
- Do **not** auto-create dual-control records; provide copy-paste ids for operators / future UI

### L3 — Export v2 complete
Human-readable section order:
1. Disclaimer  
2. Gate / process status  
3. System-observed cues  
4. Officer notes (human)  
5. Hash / schema / product metadata  

JSON export remains canonical. Markdown + HTML both match order.

### L4 — Operator dry-run documentation
`docs/demo/OPERATOR_DRY_RUN.md`:
- install/run commands
- generic mode sample
- interrogation mode with consent flags
- where outputs land
- reminder: not a lie detector

### L5 — Sample packs for demo
- Ensure `docs/examples/` has at least one clean and one conflict transcript usable by CLI
- Prefer shared fixtures with kilo where possible (`tests/fixtures` referenced from docs)

### L6 — Delivery polish
- Acknowledge/dismiss/note flows remain officer-only
- Subject never sees cue stream by default
- Neutralization pass on all user-visible strings

### L7 — End-to-end test matrix
Automated tests for:
- generic: observe → note → seal → export
- interrogation: missing consent fails; with consent succeeds
- sealed package reject further note attach
- high-priority ids appear in export when present

### L8 — Optional HTML static review page
Single-file or docs-site page that renders a sealed package JSON dropped in / pasted (client-side only) for human review — disclaimer first. No auto-findings.

### L9 — TODO.md hygiene
Update glyph-owned checkboxes that are actually done; do not mark iceman/kilo items.

### L10 — Ongoing
Poll `agent_notes/`; adapt to cue_id scheme changes from kilo; keep suite green.

## Out of scope
Observer algorithms, hash cryptography, Axon live integration.

## Long-sprint done when
CLI is session-correct for generic + interrogation; dual-control handoff visible; export v2 + dry-run doc; E2E tests green.
