# DIARY.md

Project log. Newest entry first. Short, dated, factual. See `GAMUT.md`.

## 2026-11-11 - MediaMan: media filed, ENG REQUEST, known gaps

ENG REQUEST: `src/cueliez/delivery/dashboard.py` inserts cue text into the page via `innerHTML` without HTML escaping (message, cue_id, category, source quote text). Reproduce: push a cue whose `message` and `source_quotes[].text` contain `<img src=x onerror=alert(1)>` to `LiveDashboardServer`, load the page. `docs/site/review.html` already has an `esc()` helper. Raised to the project manager for a decision on priority and owner.

Filed to `docs/training/media/{gov,leg,med,thrp}/`: `overview.png`, `workflow.png`, voiced `intro.mp4` (real dashboard and sealed-package review, synthetic transcripts, platform TTS). Two small code changes were committed to main before media-agent boundaries applied: `6a12c08` (dashboard source-quote fallback to `text`) and `0f0e278` (review page derives cue rows from observations). Existing pytest suite passed locally; the full GAMUT.md check set was not run. Lead dev to review.

Not verified to the current media standard:
- Audio transcription against the script was done for gov only. leg, med, thrp audio was not transcribed.
- No OCR check of on-screen text at the compressed size, and no language-rule scan of captions, audio or filenames, on any video or screenshot.
- Caption/audio sync was checked by frame comparison on gov only.
- Scripts are not verbatim from `docs/demo/DEMO_SCENARIOS.md`: gov and leg splice turns from two scenarios, gov splits interviewer lines across two voices, and thrp uses a transcript written by the media agent. These need to be redone from verbatim scenarios.

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
