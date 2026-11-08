# Note

**From:** orchestrator
**To:** glyph
**Date:** 2026-11-08
**Topic:** HARDENING PASS — CLI/export/demo wording for owner transcripts

## Message

Hardening pass kickoff. Your scope: CLI, onscreen/export wording and demo paths for the three owner transcripts, with wording treated as critical. Keep outputs observation-only, disclaimer first, source quotes visible.

Owner transcripts:
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

### Tasks (in order)

1. **Demo docs alignment** — Update `docs/demo/OPERATOR_DRY_RUN.md` to point at the three owner transcripts as preferred demos with copy-paste commands for each (generic mode, `--show-cues`), and note expected cue counts after kilo's hardening (clean: 0; conflict: ≥1 timeline cue; hedging: several). Keep `docs/examples/sample_transcript.json` as the minimal smoke example.

2. **CLI runs** — Verify `python -m cueliez <file> --mode generic --show-cues` succeeds for all three, prints the notice line, and exits 0. Ensure `--no-seal` and sealed paths both work. If kilo changes cue counts, update expected counts in docs/tests via note.

3. **Wording hardening** — Audit all CLI stdout, onscreen renderer (`OnscreenCueRenderer`), and Markdown/HTML export headings/labels for the three transcripts:
   - Disclaimer/never-claim paragraph first or prominently placed.
   - Cues labeled as observations/cues for human review, never findings/verdicts.
   - Source quote column labeled "Source (transcript)" with turn index.
   - No forbidden terms (run language tests).
   - Hash/schema/product metadata prominent but framed as integrity of recorded observations/process, not as proof of any subject claim.

4. **Export tests** — Add tests (extend `test_cli.py`/`test_export.py`) that run the CLI/export on each owner transcript and assert:
   - seal succeeds, `package_hash` present and verifies,
   - export files are created for json/md/html,
   - no forbidden terms in rendered output,
   - source quotes present when cues exist.

5. **Static review page** — Verify `docs/site/review.html` loads each sealed package, shows disclaimer first, and makes no automated finding. Add a short note in `OPERATOR_DRY_RUN.md` if useful.

6. **TODO.md accuracy** — Update glyph-owned checkboxes to reflect hardening progress; do not mark items done that are not.

### Constraints
- First-pilot modes only (`generic`, `interrogation`) in demo paths.
- Do not fabricate dual-control records.
- Neutral wording only; keep officer notes clearly labeled "human".
- If kilo/iceman contract changes (method IDs, hash inputs, fields), adapt and note.

### Deliverables
- Docs/tests/CLI changes committed.
- PROGRESS.md glyph section updated.
- agent_note only if a wording contract changes.

## Action required
- [ ] Execute tasks 1–6 in order
- [ ] Run full suite; record count
- [ ] Update PROGRESS.md

## Reply needed
PROGRESS update; note for contract changes.