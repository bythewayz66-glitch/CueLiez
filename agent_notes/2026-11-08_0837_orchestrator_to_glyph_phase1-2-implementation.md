# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** IMPLEMENT Phase 1+2 — officer delivery, real-time UI, latency, disclosure

## Message

Implement Phase 1+2 now (owner demand). Your scope: officer-facing delivery (subject not shown), real-time cues, latency optimization, disclosure wording.

### Tasks (in order)
1. **Officer-facing delivery** — Implement onscreen overlay/tablet cues the subject does not see by default; turn-linked/glanceable; acknowledge/dismiss/note capture. (Minimal exists; harden for real-time.)
2. **Officer note field** — Ensure high-priority cue note capture is sealed when present; verify after changes.
3. **Latency** — Measure and optimize end-to-end text cue latency on local/private-cloud (target <1–2s); document.
4. **Confidence display** — Surface confidence/model_id in delivery surfaces without overclaim; neutral wording.
5. **Disclosure/wording** — Keep exports/site/demo wording aligned; no accuracy claims.
6. **Tests/docs** — Update demo docs and tests; keep suite green.

### Constraints
- First-pilot modes only in demo paths.
- Neutral wording only.
- No fabricated deployment status.

### Deliverables
- Docs/tests/UI changes committed by you.
- PROGRESS.md glyph section updated.
- agent_note for wording/contract changes.

## Action required
- [ ] Execute tasks 1–6
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for wording/contract changes.