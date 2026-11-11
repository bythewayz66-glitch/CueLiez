# DIARY.md

Project log. Newest entry first. Short, dated, factual. See `GAMUT.md`.

## 2026-11-11 — Lead dev onboarding and baseline

Verified at HEAD `df0f0df` on a fresh clone:
- `pytest -q`: all pass, 1 skipped (`tests/test_pollinations_probe_optional.py`, opt-in network probe).
- All five CI hygiene scripts pass: fake-code scan, tracked artifacts, version consistency (0.2.0), CLI contract, schema/export/gate contract.

Findings, confirmed by running them, not yet fixed:
- `src/cueliez/ingest.py` `validate_transcript_turns` accepts turns with no usable content (`{"role": "subject"}` and blank text both pass through as `text: ""`), and carries a "Be permissive" comment. For an admissibility product, an empty or unmappable turn should be rejected or explicitly reported. Needs a decision on strictness from product, then a fix and tests.
- `src/cueliez/ingest.py` `normalize_transcript` returns an empty list for an unrecognised wrapper object (`{"foo": "bar"}`) instead of raising.
- `TODO.md` Phase 9.9 refers to `DIARY.md`; it did not exist until now.
- No pull requests or branches exist besides `main`.

Workflow decision (owner): all changes are pushed directly to `main`; no pull requests.

Open product questions: ingest strictness for empty or unmappable turns.
