# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** PHASE 0 CLOSEOUT — GitHub Pages live + landing page wording

## Message

Phase 0 closeout kickoff. Your scope: make GitHub Pages live and ensure landing page + docs emphasize “Not a lie detector.” No code/dependency changes required unless needed for Pages.

### Tasks (in order)
1. **GitHub Pages** — Enable via repo settings (Source → GitHub Actions) if not already; verify site deploys to `https://bythewayz66-glitch.github.io/CueLiez/`. If settings cannot be changed via CLI, document the manual step in `docs/demo/` or README and note it.
2. **Landing page wording** — Audit `docs/site/index.html` (and `ops.html`/`review.html`) for forbidden terms and ensure first mention expands CueLiez and states “Not a lie detector” / observation-only framing. Run language checks.
3. **Docs consistency** — Ensure README/docs/PITCH emphasize observation/cues, not detection; reference never-claim paragraph where appropriate.
4. **Tests** — Add/extend a test (e.g., in `test_cli.py` or a new `test_site_language.py`) that scans shipped site/docs text for forbidden terms (if feasible without overreach).

### Constraints
- First-pilot modes only in demo paths.
- Neutral wording only; no verdict/deception/guilt/diagnosis language.
- Do not fabricate deployment status; document actual state.

### Deliverables
- Docs/site changes committed by you.
- PROGRESS.md glyph section updated.
- agent_note if deployment requires manual action.

## Action required
- [ ] Execute tasks 1–4
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for deployment/manual steps.