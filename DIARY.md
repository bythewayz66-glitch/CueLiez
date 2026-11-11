# DIARY.md

Project log. Newest entry first. Short, dated, factual. See `GAMUT.md`.

## 2026-11-11 — Officer UI sprint 1: output escaping across delivery surfaces (officer UI engineer)

Labels: [ran] executed and observed, [read] read the code. Scope: `src/cueliez/delivery/*`, `docs/site/review.html`, their tests and docs. Closes ENG-006 for the delivery modules.

**Reproduced [ran]:** the live dashboard did run transcript-derived markup. In Chromium, with the pre-fix code, a pushed cue whose `message` and `source_quotes[].quote` held `<img src=x onerror=...>` set `window.__pwned` to `message` and `quote` (the `q.text` fallback payload from `6a12c08` went through the same sink; its `<svg onload>` handler did not set its flag in my single read, cause not investigated). Cause: `dashboard.py` built the card with string concatenation into `innerHTML`. MediaMan's report was correct. `0f0e278` (review page rows from observations) was not exploitable: the review page already ran every value through `esc()`; I rewrote it anyway to build nodes with `textContent`.

**Every place transcript, cue or officer text reaches output [read], and status:**
1. Live dashboard client JS: cue `message`, `priority` (also a class name), `category`, `cue_id`, `turn_index`, `score`, `source_quotes[].quote/.text/.turn_index`, fetch error text. Was `innerHTML`; now `createElement`/`textContent`, `priority` allow-listed for the class, non-object cues/quotes and non-numeric scores tolerated (a string `priority` used to throw and blank the page).
2. `/cues` JSON endpoint: JSON only; now `nosniff`, `no-store`, `no-referrer`.
3. `render_officer_html`: title (x2), `priority`, `cue_id`, `label`, `turn`, `message`, `method`, quote `role`/`turn`/`text`, and `data-*` attributes (already `html.escape`d, now via `escape_html`), plus the inline `<script type="application/json">` cue block. That block was `html.escape`d, which is wrong context for a script: a payload could not break out, but the JSON was mangled for any reader. Now `json_for_script` (ASCII JSON, `<`, `>`, `&` as `\uXXXX`), round-trip tested.
4. `render_html`: title, priority, turn, category, message, method, evidence JSON, quotes. Already escaped; now through `escape_html`.
5. `render_text` (terminal): message, category, cue_id, method, evidence, quote role/text, header. Terminal escape sequences (OSC/CSI), bidi overrides and C1 controls passed through raw; now shown as `[U+XXXX]`.
6. `docs/site/review.html`: priority, turn, cue_id, label, score, message, officer note `cue_id`/`action`/`note`, disclaimer, epistemic status, definitive-finding flag, product, versions, hash, sealed_at, mode, consent/training, error text. Was escaped `innerHTML`; now DOM nodes. Rendered text compared old vs new in Chromium for all three owner packages: identical.
7. Not in my modules, observed only: `export.py` `render_package_summary_html` (CLI `.summary.html`). Sealed a hostile transcript through the CLI and parsed the output: no script/img/`on*` attributes, payload shown as `&lt;img`. Looks safe [ran]. `training_gui.py` writes `JSON.stringify(...)` into `innerHTML` inside `<pre>` (sandbox, records pages) with the sandbox cue text, which comes from a transcript: see ENG REQUEST.

**Tests [ran]:** `tests/test_delivery_escaping.py` (28 test methods, many subtests) and `tests/js_dom_harness.py`. The harness runs the real inline scripts under Node against a recording fake DOM (records every `innerHTML` write and every created element/attribute), and parses server HTML with the stdlib parser. Payloads: `<script>`, `"><img onerror>`, `</script><script>`, attribute-breaking quotes, `javascript:`, svg/iframe srcdoc/mXSS, entity-encoded and fullwidth lookalikes, ANSI, bidi, line separators, NUL, C1. Before the fix: 52 failures (incl. subtests) on this file; after: all pass. Client-side tests skip locally without Node and fail in CI (`CI` env var) if Node is missing. I did not verify that the CI runner image has Node; if it does not, CI will fail on these tests and Node must be added to the workflow (`.github/` is not my module: lead dev).

**Also changed:**
- CSP. Dashboard: response header on `/`, hash-pinned inline script and style, `default-src 'none'`, `connect-src 'self'`, `frame-ancestors 'none'`, no `unsafe-inline`. Officer HTML and review page: meta CSP with hashes (meta cannot carry `frame-ancestors`). Observed in Chromium that the review page policy blocks even a same-page `fetch`.
- Dashboard origin check: was `startswith("http://127.0.0.1")`, so `http://127.0.0.1.evil.example` and `http://localhost.evil.example` were accepted (and a cross-origin POST could replace the cue list). Now exact parsed-host match on `127.0.0.1`, `localhost`, `[::1]`; tested, including a cross-origin POST that must leave cues unchanged. Token auth and rate limit untouched and their existing tests pass.
- New `delivery/safe.py`, `docs/DELIVERY_OUTPUT_SAFETY.md`.

**Browser results [ran, bundled Chromium]:** old code + hostile cues: `window.__pwned` set, 3 injected `img/svg` elements. New code: hostile transcript (4 payloads in subject turns, sealed through the CLI) on the live dashboard: 8 cues, 0 injected elements, `__pwned` unset, payload text visible literally. Review page: hostile package (cue ids, notes, disclaimer) and the three owner packages: 0 injected elements, `__pwned` null, owner output text byte-identical to the old page. Officer HTML with a hostile title and notes: 0 injected, acknowledge button works under the CSP, notes JSON correct. I did not test Firefox/Safari. I did not test the dashboard page with the token enabled in the browser.

**Checks [ran, merged tree on main 2f9d3a2]:** `check_no_fake_code` FAKE_CODE_SCAN_OK; `check_no_tracked_artifacts` ARTIFACT_CHECK_OK; `check_version_consistency` VERSION_CHECK_OK 0.2.0; `python -m cueliez --help` exit 0; `check_cli_contract` CLI_CONTRACT_OK; `check_contracts_phase9` CONTRACTS_OK; `pytest -q` all passed, 1 skipped (pre-existing). Delivery tests also run on Python 3.10 and 3.13 earlier in the session; the last 3.10/3.13 rerun was interrupted, so treat those as unconfirmed for the final tree.

**Open:**
- Officer notes: acknowledge/dismiss/note are still not labelled as human actions in the live dashboard (it has no actions). Not started this sprint.
- Accessibility pass, explicit subject-not-shown control: not started.
- Dashboard has no token-in-browser flow tested.

ENG REQUEST: training_gui.py owner. `/sandbox` and `/records` pages put `JSON.stringify(response)` into `innerHTML` inside `<pre>`; the sandbox response contains cue text and quotes from the pasted transcript, so `</pre><img onerror=...>` in a transcript executes. Use `textContent`. I have not reproduced this in a browser.

## 2026-11-11 — Independent review, first pass (Reviewer)

Basis: clean clones in fresh venvs. Full GAMUT.md check set run on each of 6a12c08, 0f0e278, b50ea6d, df0f0df and HEAD 75541c4: fake-code scan, tracked-artifact scan, version check, `--help`, CLI contract, contracts phase 9 all OK; `pytest` 394 passed, 1 skipped (opt-in Pollinations probe), 99 subtests, on every commit. Also pytest on Python 3.10.12 and 3.13.17 at 75541c4: same result. I did not run 3.12. I wrote no code; no reviewed file was changed.

REVIEW 6a12c08 — FAIL (behaviour correct, not done per GAMUT.md item 3)
- Fix is right: quotes built by `delivery/events.py` use key `text`, never `quote`. Ran `LiveDashboardServer` with cues from a real sealed owner_conflict package in a browser: before the fix every source line rendered `""`; after, the real quote text. Change is one token, nothing else moved.
- No test fails without it. Reverted the fix, ran the suite: 394 passed. `tests/test_dashboard.py` never loads the page JS or posts `source_quotes`. Needed: a test that posts a cue with `source_quotes[{text}]` and asserts the rendered page or its template uses `q.text`.
- Same page inserts `message`, `cue_id`, `category`, quote text via `innerHTML` unescaped. Reproduced: cue `message` `<img src=x onerror="window.PWNED=1">` set `window.PWNED` in the browser; `<b>`, `<i>` in category and quote also became DOM elements. Reported to ENG, not fixed by me.
- `LiveDashboardServer` is referenced nowhere in `cli.py`, `session.py` or `__main__`; nothing starts it or posts cues to it. `TODO.md` lines 38 and 114 mark it done as an officer UI; it is defined but not reachable.
- Author is the media agent; commit has no DIARY entry; author admits the full check set was not run (it passes, I ran it).

REVIEW 0f0e278 — FAIL (behaviour works, not done per GAMUT.md item 3)
- File changed is `docs/site/review.html`, not `src/cueliez/delivery`. Matches its message.
- Real sealed package (CLI, owner_*.json, interrogation) has no top-level `cues`; its observations carry `cue`, `cue_id`, `priority`, `turn_index`, so the fallback is the live path. Rendered in a browser: conflict 2 rows from 2 observations, clean 0 rows ("No cues present"), hedging 8 rows from 8 observations. Every observation shown once, none duplicated.
- Mislabel/inconsistency: review page prints observation priority `normal`; the CLI's own `.summary.md/.html` for the same package print `medium` and order rows by priority/score; review page keeps observation order. Footer still says "If the package stores cues separately... otherwise cues may be derived by external tools", now untrue. Source quotes and method are not shown. If a package ever carries `cues: []`, `Array.isArray` returns the empty list and the fallback is skipped.
- Escaping: `esc()` is applied to every field. Payload with `<img onerror>` in disclaimer, label, cue_id, turn_index and officer note: no script ran, 0 `<img>` elements in `#out`.
- No test fails without it: reverted, 394 passed. `tests/test_site_language.py` only scans the file for forbidden words. Needed: a test that renders a package without `cues` (Node/jsdom or a Python-side contract test of `cuesFrom`).

REVIEW 8d2fd70 — PASS WITH NOTES (gov/intro.mp4)
REVIEW 4278d94 — PASS WITH NOTES (leg/intro.mp4)
REVIEW 9b9a40a — PASS WITH NOTES (med/intro.mp4)
REVIEW df0f0df — FAIL (thrp/intro.mp4)
- All 12 files under `docs/training/media/{gov,leg,med,thrp}/` exist (overview.png, workflow.png 1280x720; intro.mp4 h264+aac, 61-80 s). Started `--training-gui` on 127.0.0.1:8765: all 12 `/media/...` URLs return 200 with the exact repo byte sizes; in Chromium every image loads at 1280x720 and every video loads (duration 80/76/61/72 s).
- Language: transcribed all four audio tracks (whisper) and OCR'd every caption frame. No forbidden phrase in audio, captions or on-screen text. "lie detector"/"polygraph" appear only inside the product disclaimer on the review page ("is not a lie detector... not a polygraph"). Captions ("never diagnosis or credibility judgments", "observations for the officer, not findings", "the officer decides") are not stronger than OWNER_DECISIONS section 1. The med tail "I don't know" x4 in the transcript is a Whisper artifact over 20 s of silence, not video content. Neither "Cue + Legal Interview Engine" nor the never-claim paragraph appears in any video (LANGUAGE_RULES first-mention rule).
- df0f0df FAIL: the on-screen cues cite the therapist's own question (T0 "How have things been since our last session?") as source for "Account uses general/vague references; ask for who/what/when/where specifics", "First-person reference pattern shifted" and the convergence cue. Reproduced from the CLI with `--mode therapy`: source line reads "(T0, therapist transcript)". Cause: `observations/base.py is_subject_turn` knows `clinician`, `interviewer`, `officer` but not `therapist`, and unknown roles default to subject. The video teaches a trainee that observers cue the interviewer. Re-record after the role fix; same root as ENG-002.
- Notes: (1) Step 3 caption "Seal the record ... with package hash" is on all four; the exported file from that flow fails `--verify-package` (ENG-001, which I reproduced). (2) med overview/video cue "Response qualifies memory/certainty; distinguish direct recall from reconstruction" is the closest to a reliability judgement in any frame; product to decide if it stays in clinical-context training. (3) med and thrp (and gov) are outside the first-pilot messaging scope in OWNER_DECISIONS section 2; the repo is public. (4) Training GUI shows "Intro video (webm): No media file provided yet" and the server's absolute path next to the working mp4 on every module page (`training_gui.py` lines 112-125, 205-220). (5) Replacement mp4s are committed as "Add" over earlier versions (bb6ffdc, 206dc60, a931f6a, f2f47df); no generation script is in the repo, so the media cannot be reproduced; MediaMan's own entry says gov/leg scripts are spliced and thrp is not from DEMO_SCENARIOS.md.

REVIEW b50ea6d — PASS WITH NOTES (GAMUT.md, DIARY.md)
- Every command in GAMUT.md exists and passes; the list equals `.github/workflows/ci.yml` order. 3.10 and 3.13 pass. Lead's DIARY claims verified: `validate_transcript_turns([{"role":"subject"}])` returns an empty-text turn; `normalize_transcript({"foo":"bar"})` returns `[]`; "Be permissive" comment at ingest.py:141; only `main` exists on the remote.
- Inaccurate or missing: (1) "Run from the repo root with `src` on the path or the package installed" is true (`check_cli_contract.py` exits 1 "--help failed" without it) but pytest is also absent from a bare environment and no install line is given: add `python -m pip install -e ".[test]"`. (2) "Do not commit .venv, uv.lock, build/, dist/, *.egg-info or bytecode" is not enforced: `check_no_tracked_artifacts.py` checks only `build/`, `dist/`, `__pycache__`, `.pyc`, `.pyo`; `.gitignore` has no `uv.lock`. Nothing tracked today (`git ls-files` grep empty). (3) The definition of done bans "fake return values", but `check_no_fake_code.py` scans three text patterns in `src/` only; reviewers, not CI, carry that. (4) The "no explanatory notes in code" rule is not met by existing code (for example ingest.py:141, multi-paragraph docstrings in gates.py); treat as a standing cleanup, not a regression.

Baseline at 75541c4
- Stubs and fake returns in src/: none found. AST scan for empty-body or constant-return defs: 0; markers TODO/FIXME/NotImplemented: 0 (matches fake-code script); remaining word hits are argparse "placeholder" help text and an HTML textarea placeholder. Broad `except`: 31 in src/, 7 that only swallow. Read all. Needs action: `observations/assisted.py:136` swallows any adapter failure under a comment saying "fail closed" (it drops the observer silently, no record); `gates.py:488 sign_package` turns a signer exception into `package_signature: {"type":"error"}` and still seals (CLI guards a missing key, not a runtime error); `compliance/records.py:154` silently skips corrupt record lines; `ingest.py:188` fallback re-reads unvalidated input after any failure (PM's ENG-002). Acceptable and commented: audit logging, import fallbacks.
- Seal-time language gate is narrower than AGENTS.md section 2 ("reject any observation or annotation that uses verdict language or banned keys"). Ran against `seal_observation_package` in generic mode: label `subject_is_lying` SEALED, `deception_detected` SEALED, cue text "The subject is lying; guilty." SEALED, observation key `guilty`/`diagnosis` SEALED, nested annotation `{"x":{"guilty":true}}` SEALED, top-level `truth_score` kept in the sealed package. Blocked: exact label `Lying`, top-level annotation key `Guilty`, `is_definitive_finding: true`. Cause: `FORBIDDEN_OBSERVATION_LABELS` is exact match on 8 words; banned keys are checked only on top-level `annotations`; no other layer checks (grep).
- Tests that cannot fail: 14 test functions with no assertion. Ten are valid: eight "does not raise" positive paths paired with failing-path tests (consent, training, dual-control, allowed uses, modality) and two that assert through a helper. Weak: `test_observations_consistency.py:50 test_self_reference_shift` (comment: "may or may not trigger", only seals the result) and three `test_empty_safe` tests (only seal an empty list). No constant asserts. 1 skip (opt-in network probe). Broad `except` in tests is used in helper servers/parsers, one `self.fail` wrapper: fine.
- TODO.md: 71 items are `[x]`; I verified 21 against code, by running unless marked [read].
  Backed: CLI to sealed package + cues (L16, ran owner_*.json); assisted observers off by default (L24/L35, ran: `multi_signal` appears only with `--enable-assisted`); insufficient-data states (L27, tests with assertions); consent and training fail closed (L55, ran: `consent_required`, no files written, `signing_key_missing` writes nothing); dual-control (ran: no records -> `dual_control_incomplete`, same officer twice -> `dual_control_same_officer`, two distinct officers seal); forced `observed_indicator` (L142, ran; `is_definitive_finding: true` is rejected); training version in package (L147, `gate_state.training_version: v1`); score/model_id/label enforced (L152, [read] `_validate_observation_entry`); reproducible observations (ran twice, identical); SSRF hardening (L246, ran 10 URLs: metadata, RFC1918, CGNAT, userinfo, file:, ftp:, 0.0.0.0 blocked; loopback incl. `::1` allowed as documented); zero runtime deps; language audit of shipped text (grep: only refusal/negation contexts).
  Partly backed: banned keys/verdict labels at seal (L50) and "never records findings" (L65, L162): see seal gap above. "Full gate state + cues + observations exported" (L157): JSON has gate_state and observations but no top-level `cues`; cues appear in md/html only. Version consistency (L202): checks only pyproject vs `__init__` ([read]); the item admits the rest. Hash/signature at seal: true in memory, false for the exported file (below).
  Not backed: "Admissibility & Disclosure Guide exists and is accurate" (L169): the exported file fails the product's own check, see ENG-001. "signed/structured JSON + PDF" (L60): no PDF code in src/ (grep), and the same line says signing is not implemented while `--sign` exists. Officer UI/real-time dashboard (L38, L114): `LiveDashboardServer` unreachable from the CLI. Retention docs (L78): docs exist, `retention.py` has 3/5/7-year defaults and no importer (grep).
- ENG-001 (PM) independently confirmed: `python -m cueliez docs/examples/owner_conflict_interview.json --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1 --out-dir D --basename conflict` then `--verify-package D/conflict.json` returns `hash_ok: false`, exit 2; with `export_notice` and `exported_at` removed it returns `hash_ok: true`, exit 0. Extends to signing: with `CUELIEZ_SIGNING_KEY=k1`, `--sign` export then `--verify-package` with the same key gives `ok: false`, `hash_ok: false`. `scripts/check_contracts_phase9.py` hashes the in-memory package and never verifies an exported file, which is why CI is green.

What must change, in order
1. ENG-001: exported package must pass `--verify-package` (signed too); add a test through the real CLI export path.
2. Seal gate: reject verdict language in observation labels, cue text and keys, and banned keys at any depth, and any banned top-level key; tests for each.
3. Add regression tests for 6a12c08 and 0f0e278; escape `dashboard.py` output (in progress); decide whether the officer dashboard is wired to the CLI or `TODO.md` L38/L114 are relabelled.
4. Role handling: unknown or unlisted roles (`therapist`) must not default to subject (ENG-002); then re-record thrp/intro.mp4.
5. review.html: align priority vocabulary and ordering with exports, fix the stale footer, handle `cues: []`.
6. Training GUI: do not show "no media" for the optional webm; do not print server paths.
7. Relabel `TODO.md` items listed under "Not backed" and "Partly backed"; PM list in the 2026-11-11 PM entry agrees on PDF, retention, vendor adapters.
8. Replace the three weak observer tests with assertions; make `assisted.py` and `sign_package` failures visible instead of swallowed.
9. GAMUT.md: add install line; make artifact check match the rule or soften the rule.
Tool notes: runner and scanner are in the reviewer workspace skill `cueliez-clean-check`; scanner hits are leads that I read by hand.

## 2026-11-11 — Ingest sprint 1: fail-closed ingest, empty-turn policy, silent-drop audit (ingest/connectors engineer)

Labels: [ran] executed and observed, [read] read the code. Changes are in `src/cueliez/ingest.py`, its tests, fixtures and docs only.

**Done (ENG-002 library side, lead-dev tasks 1-3):**
- `normalize_transcript({"foo":"bar"})` now raises `IngestError` (`ValueError` subclass, `.code`, `.turn_index`, `.as_dict()`). Before [ran]: returned `[]`. Also raises for non-list containers, a non-sequence root, `None`, null/number/list turns, unreadable or invalid JSON (was a raw `JSONDecodeError`/`FileNotFoundError`), two recognised containers in one wrapper (was: first silently won, second dropped), zero turns and recognised-but-empty containers.
- Empty turns follow the PM decision (section C of the PM entry): mapped role + empty text is kept in place, flagged `ingest_flags: ["empty_text"]`, counted in `source_artifact.ingest_report` (inside the package hash; test edits the report and `verify_package_hash` goes false). Unmappable or missing role is rejected `ingest_unattributed_turn` with turn index and original label. All-empty transcript is rejected. "Be permissive" comment removed.
- Policy switch: `ingest.EMPTY_TEXT_POLICY` (default `"flag"`, the PM decision, so not provisional). `"reject"` is also implemented and tested; a one-line change, or `empty_text_policy=` per call. Under `reject`, an empty turn that carries timing or feature keys (silence segment) is still kept and flagged; other empty turns raise `ingest_empty_turn`. Rule and key list are in the contract doc. This answers the ENG-002 open question: a silence segment keeps its timing/feature metadata and is flagged `empty_text`.
- Removed the `except Exception` fallback in `load_transcript` that re-read input without validation.
- Further silent drops found [ran] and fixed: `{"text":"","utterance":"hello"}` lost "hello"; a second wrapper container was dropped; any nested/list/dict key on a turn was dropped; `words` timings were dropped; conflicting role or text fields were resolved by key order. Now: every unused key is copied through, conflicts raise `ingest_ambiguous_turn`, wrapper keys that are not turns are listed in `ingest_report.ignored_wrapper_keys`. `canonicalize_turn` no longer returns a blank turn for a non-mapping.
- Fixtures: `tests/fixtures/transcripts/vendor/` (one per wrapper key, role alias, text alias, silence segment) and `malformed/` (15 files, each mapped to a code). Tests: `tests/test_ingest_strict_sprint1.py`. A test parses `docs/TRANSCRIPT_INGEST_CONTRACT.md` and compares its key lists, empty-policy default, error codes and report fields to the code.
- Docs: contract rewritten to match; `GATE_ERROR_CODES.md` lists the 8 new codes; `INTEGRATION_SPEC.md` section 2 updated.

**Verified [ran]:** `scripts/check_no_fake_code.py` FAKE_CODE_SCAN_OK; `check_no_tracked_artifacts.py` ARTIFACT_CHECK_OK; `check_version_consistency.py` VERSION_CHECK_OK 0.2.0; `python -m cueliez --help` exit 0; `check_cli_contract.py` CLI_CONTRACT_OK; `check_contracts_phase9.py` CONTRACTS_OK; `pytest`: 432 passed, 1 skipped, 180 subtests passed. All 22 transcript JSON files under `docs/examples` and `tests/fixtures` still ingest.

**Existing tests I had to edit (inputs only, assertions unchanged):** role `"i"` became `"interviewer"` in `test_finish_remaining_iceman_0904.py` and `test_ingest_connectors_phase7_iceman.py`; `{"text":"x"}` got `"role":"subject"` in `test_ingest_phase7_iceman.py`. `test_ingest_vendor_normalization_kilo.py::test_validation_rejects_invalid_root` asserted the old behaviour (`validate_transcript_turns(None) == []`, null turns skipped); it now asserts `None` raises. These inputs are invalid under the PM decision.

**NOT done / open:**
- The CLI does not use `cueliez.ingest` at all [read: `cli.py` `_load_transcript`]. Observed [ran] on the new malformed fixtures with `--no-seal`: `[]`, a null turn, an unmapped role and all-empty turns exit 0 and emit a package with `observations: []`; only the two wrapper cases exit 2. So at the CLI, ENG-002 ACs 1-4 are not met yet. See ENG REQUEST below.
- ENG-003 (hash of raw input bytes) not started; depends on ENG-001 which is not mine.
- Oversized-input cap for transcripts (standing goal) not implemented; connectors keep theirs. Needs a number from the lead dev or PM.
- `connectors.py` never calls ingest (it moves sealed packages), so no connector change was needed. Connector config validation, idempotency, retry policy and audit events from the roadmap are not started this sprint.

ENG REQUEST: cli.py owner. Replace `_load_transcript` (and the `--stream-turns` per-turn path) with `cueliez.ingest.load_transcript` / `normalize_transcript_with_report`. The existing top-level handler already prints `error_code` for exceptions with `.code` and exits 2, so `IngestError` needs no extra handling. Pass `ingest_report` into the package `source_artifact` so sealed CLI packages carry it (ENG-002 AC4). Priority: high, a null turn or unattributed turn can currently reach a sealed package through the CLI.

ENG REQUEST: observations/runner.py owner. `_normalize_transcript` returns `[]` for an unrecognised wrapper and knows only `turns`/`transcript`/`messages`, so `ObservationRunner.run({"utterances":[...]})` silently yields zero observations. Make it raise or delegate to `cueliez.ingest`.

ENG REQUEST: observers owner. Turns with `ingest_flags` containing `empty_text` must count as no data for latency, length-variance and similar observers, and no cue may cite them as source text (ENG-002 AC6). Library output already marks them.

**Questions for the PM:**
1. A bare string turn is accepted and attributed to `subject` by assumption. That conflicts with the attribution argument in section C. Keep, or reject strings as unattributed?
2. Diarised exports that label speakers `Speaker 1`/`Speaker 2` are now rejected `ingest_unattributed_turn` (only `speaker_a/b`, `person_a/b` map). Intended per section C; confirm before a pilot partner supplies such an export.
3. Zero turns and `[]` are rejected. Your section C said so; the lead dev asked for this to be decided deliberately, and it is documented in the contract.

## 2026-11-11 — Product manager first session: roadmap audit, ingest decision, next sprint (PM)

Basis: fresh clone at HEAD `b50ea6d`. Labels: [ran] I executed it, [read] I read the code or doc, [heuristic] script output not yet hand-checked. I did not run `pytest` or the CI scripts; I rely on the lead dev's baseline entry below for those. I have not edited `TODO.md`, `src/`, `tests/`, `scripts/` or `.github/`.

Access: connected GitHub account with admin/push on `bythewayz66-glitch/CueLiez` [ran: API permissions]. The repo is public [ran]. My working tools live outside the repo in the agent workspace (`language-compliance-check`, `roadmap-status-audit`, `acceptance-criteria-writer`, `pilot-readiness-checklist`).

### A. New defect found while building the pilot checklist (highest priority)

A sealed package exported by the CLI fails the CLI's own `--verify-package`. [ran] Steps: `python -m cueliez docs/examples/owner_conflict_interview.json --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1 --out-dir D --basename a`, then `python -m cueliez --verify-package D/a.json` gives `hash_ok: false`, exit 2. Removing only `export_notice` and `exported_at` from the file makes `verify_package_hash` return true. `export.py` adds those two keys after seal and `_canonical_json_for_hash` in `gates.py` does not exclude them. Existing verification tests (`tests/test_cli_verify_sign_phase9.py`, `test_long_sprint_iceman.py`) check the in-memory sealed package, not a file written by the CLI export path. Consequence: the artifact an operator would attach as the original record does not verify under the product's own check, and the integrity statement in `docs/ADMISSIBILITY_AND_DISCLOSURE.md` and `docs/PILOT_VALIDATION_METRICS.md` is not true of exported files. Raised as ENG-001. Everything the roadmap says about hash integrity is true of the in-memory seal only until this is fixed.

### B. Roadmap audit: `[x]` items that are docs-only, partial or unverified

[heuristic] `roadmap-status-audit` on `TODO.md`: 71 items marked `[x]`. Cited evidence is code or tests and uncaveated for 6; code or tests plus an admitted limit for 9; docs only for 7; no path, test or module cited for 49 (uncited is not the same as not done). 8 items are `[~]`. The list below is what I checked by hand against the code. [read]/[ran] as marked. Nothing here is a claim that a feature is broken, except where stated.

Claims the repo does not support as worded (proposed re-label; lead dev to confirm before I edit `TODO.md`):

1. Phase 3.3 "signed/structured JSON + human-readable PDF" `[x]`. No PDF code exists in `src/` [read]. Exports are json, md, html (`--format`). Re-label: "JSON, Markdown, HTML; PDF by browser print only".
2. Phase 3.3 hash item says "signature not yet implemented" and the Admissibility checklist says "signature optional hook". Stale: `src/cueliez/signing.py` and `--sign`/`--verify-package` exist (item 9.6) [read]. Update the text.
3. Phase 7 "Live Axon / CaseCracker / RMS integration" `[x]`. No vendor-specific code in `src/` [ran: grep]; `connectors.py` is a generic HTTP push/pull, tested with mocked endpoints. Item 9.7 itself says vendor adapters wait for partner scope. Re-label: "generic HTTP connector, mocked tests; no vendor integration".
4. Phase 4 retention "Document data-retention and access controls" `[x]`. Docs only. `src/cueliez/retention.py` exists but nothing imports it and no test covers it [ran: grep]; it also hard-codes 3, 5 and 7 year defaults with no recorded source. Raised as ENG-004.
5. Phase 5 "Measure and report latency, completeness of packages, and gate compliance in pilots" `[x]`. No pilot has run, and there is no tool that produces p50/p95 [read: `scripts/`]. It is a documented plan. Re-label `[ ]` with note "manual path documented". Raised as ENG-005.
6. Phase 5 "Target early pilot agencies..." `[x]`. `docs/demo/PILOT_PREP.md` describes a target profile. No agency is identified and the item's own text says outreach is pending. Re-label `[~]`.
7. Phase 5 "private red-team / synthetic ... transcript set" `[x]`. The fixtures are in `tests/fixtures/redteam/` of a public repository, so they are not private, and the item admits the broader set awaits partner data. Re-label: "synthetic red-team fixtures (public)".
8. Phase 2 "end-to-end latency < 1-2 seconds" `[x]`. Single local manual measurement recorded in `docs/demo/VALIDATION_NOTES.md`; no timing test or script [read]. Re-label: "measured once locally; not regression-tested".
9. Phase 0 "Add minimal real dependencies (pydantic, numpy/scipy)" `[x]`. Closed by a decision not to add any (`pyproject.toml` has `dependencies = []`). Re-label: "descoped by decision 2026-11-08".
10. Admissibility checklist "Admissibility & Disclosure Guide exists and is accurate". Existence verified. Accuracy against the code is not verified (9.2 docs-versus-implementation pass is `[~]`), and finding A shows at least one statement about hash verification is untrue of exported files.
11. Admissibility checklist "Works with evidence / RMS workflows" `[x]` and Phase 4 "easy to attach as original artifacts". Docs only; no connector or export path beyond generic HTTP; finding A applies.
12. Phase 3.5 "Keep sales, training, and UI language consistent with technical reality" `[x]`. This is a standing obligation, not a completable item. My check [ran] shows `README.md` and `docs/PITCH_26S.md` do not contain the locked never-claim paragraph that `docs/OWNER_DECISIONS.md` section 1 says must be used in the README and any external description. I own this fix (sprint item M1).
13. Phase 6 "Never market accuracy..." and "Primary message..." `[x]`. Policy statements, not deliverables. Keep as locked policy; they should not be counted as completed work.
14. 9.1 "check_no_fake_code" `[x]`. The script exists and the lead dev reports it passing. The item text lists the pattern `pass  # stub`; the script does not check it, and it scans `src/` only [read]. Minor drift between text and script.

Items that hold up under my check: Pages is live (HTTP 200 at the site URL, Pages API shows a workflow build) [ran]; consent fails closed with stable code `consent_required` and writes no package [ran]; the three owner transcripts seal through the gated CLI [ran]; signing and verify flags exist [read].

Possible under-claims (items `[ ]` or `[~]` where code exists): "Real-time audio stream hooks" is `[ ]` while `src/cueliez/observations/audio_stream.py` and `tests/test_audio_stream_phase7_kilo.py` exist; 9.6 "export verification tooling" is `[ ]` while `--verify-package` exists. I have not evaluated them. Lead dev: please say what they cover.

### C. Ingest decision: reject or flag empty and unmappable turns

Recommendation: split by cause. Reject what cannot be attributed or understood; keep, flag and count what is merely empty.

Confirmed current behaviour [ran]: `[{"role":"subject"}]` and a blank-text turn pass as empty text; `[5]` becomes `{role:'', text:''}`; `{"foo":"bar"}` returns `[]`; a `None` turn is dropped, so a 3-turn input records `turn_count: 2`; a role such as `"zzz"` or a missing role passes through. Also [read]: `load_transcript` wraps `normalize_transcript` in `except Exception` and falls back to the unvalidated path, so a rejection added to `validate_transcript_turns` alone would be swallowed.

Decision for the pilot (owner may overrule):
- Reject, fail-closed, no package written: a turn that is not an object or string (including null); a turn with a missing or unmappable role; an unrecognised wrapper; zero turns; a transcript where every turn is empty.
- Accept and flag: a turn with a mapped role and empty or whitespace text. Keep it in its original position, mark `empty_text`, count it in an `ingest_report` that is sealed inside the package hash. Observers treat it as no data and no cue may quote it.
- Never drop or rewrite a turn silently.

Reasons: (1) The sealed record has to be reproducible from the stated input. Silent drops, silent empty substitutes and a turn count that differs from the input defeat that. (2) Attribution is the weak point for admissibility: an unattributed or mislabelled turn can put words in the wrong speaker's mouth, and observers compare subject statements with each other. Guessing a role is worse than refusing. (3) Real exports contain benign empty segments (silence, inaudible, non-verbal). Rejecting the whole transcript for one would push operators to hand-edit files before ingest, which damages custody more than a visible flag does. (4) A reviewer or opposing party can see exactly what was empty and where, because the flags are in the hashed artifact. (5) No threshold on the share of empty turns in v1: any number would be invented. The report makes the share visible, and a pilot can tell us if one is needed.

Tradeoff: stricter ingest will refuse some real vendor exports until their role labels are mapped. That is the intended outcome; the error names the turn and the original label so the mapping table can be extended deliberately. Raised as ENG-002. Related integrity gap raised as ENG-003: `source_artifact.transcript_sha256` hashes the normalised transcript, not the original input bytes.

### D. Proposed next sprint

Order is by pilot impact under the locked scope (`generic` + `interrogation`; first-pilot features before speculative modalities).

Engineering (acceptance criteria in the requests below):
1. ENG-001 exported package verifies, and ENG-006 dashboard and HTML output escaping (from the MediaMan request). Both priority 1; ENG-001 blocks any statement about package integrity.
2. ENG-002 ingest fail-closed with flagged empty turns.
3. ENG-003 hash of the original input in `source_artifact` (after 1 and 2).
4. ENG-004 retention module: no built-in periods; operator-supplied or removed.
5. ENG-005 pilot metrics report command (after 1).

Product (mine), each with a stated finish line:
- M1 Put the locked never-claim paragraph into `README.md` and `docs/PITCH_26S.md`. Done when `language-compliance-check --external` shows the paragraph present, no VIOLATION, and `tests/test_site_language.py` passes on a clone with my change.
- M2 Re-label `TODO.md` per section B after lead dev confirmation. Done when every re-labelled item names its evidence or its limit and `roadmap-status-audit` lists no `[x]` item that admits a limit without a label.
- M3 Pilot brief: one page stating the chosen first context (training context or single detective unit), what the partner must supply, the non-accuracy success measures from `docs/PILOT_VALIDATION_METRICS.md`, and the external prerequisites with owner and status. Done when `pilot-readiness-checklist` section 5 items each point to the brief. No outreach to anyone outside before owner approval.
- M4 Position on PDF: HTML print-to-PDF is sufficient for the pilot; no PDF library (keeps zero runtime dependencies). Reflected in docs once the owner agrees.

Pilot readiness today [ran, `pilot-readiness-checklist --run`]: 11 met, 4 not met (README paragraph, retention not wired, exported package verification, no metrics script), 1 deferred (live vendor integration, post-pilot per owner decisions), 6 open and external (partner, agency and legal approval, data source, trained operators, outreach approval, agreed success measures). Nothing in the repo shows any of the six external items exists.

### E. Questions and requests

For the owner:
- O1 Confirm the ingest decision in section C.
- O2 Confirm HTML print-to-PDF is acceptable for the pilot (M4).
- O3 The repo is public. It holds named academics' email addresses in `docs/PARTNER_CONTACTS.md` (taken from published correspondence, per that file), the "red-team" fixtures, and training media. Is public the intended posture before a pilot? I have not changed anything.
- O4 Which first pilot context do you prefer: a training context or a single detective unit? No outreach happens until you approve a named target and the wording.
- O5 Confirm the product ships no default retention periods (ENG-004).

For the lead dev:
- Confirm or correct the re-label list in section B so M2 can proceed.
- Answer the open questions inside ENG-001 and ENG-002.
- Tell me what the audio-stream hooks and `--verify-package` cover relative to the two roadmap items in section B.

Tool notes: the language checker is heuristic (per-line negation). Reading its REVIEW hits is required. The roadmap audit's grade D means "cites nothing checkable", not "not done".

### F. Engineering requests

Every request below also requires the `GAMUT.md` definition of done and the seven checks in `GAMUT.md` (fake-code scan, tracked-artifact scan, version consistency, CLI help, CLI contract, contracts phase 9, `pytest`), run and reported.

ENG REQUEST: ENG-001 CLI-exported sealed package must pass package verification

Date: 2026-11-11
**Why:** A sealed package exported by the CLI fails the CLI's own --verify-package (hash_ok false). Observed 2026-11-11 on a fresh clone: sealing docs/examples/owner_conflict_interview.json in interrogation mode and verifying the written JSON. Removing only the export_notice and exported_at keys makes verification pass, so those export-time keys are the cause. The existing verification tests check the in-memory sealed package, not the exported file. The product's integrity story (docs/ADMISSIBILITY_AND_DISCLOSURE.md, docs/PILOT_VALIDATION_METRICS.md) depends on the exported artifact verifying.

**Decisions this follows:** docs/OWNER_DECISIONS.md section 5 (hash story is integrity of recorded observations and process); AGENTS.md section 4

**In scope:**
- Make the JSON file the CLI writes verify under --verify-package and verify_package_hash.
- Add a regression test that goes through the real CLI export path.
- Update docs/schemas/sealed_package_v1.md and docs/ADMISSIBILITY_AND_DISCLOSURE.md if the hash coverage description changes.

**Out of scope:**
- Choice of mechanism (exclude export metadata from the hash, move it outside the package, or cover it): engineering decides and reports which in DIARY.md.
- Backward compatibility for files exported by earlier versions: the roadmap and repo record no pilot, so none is required.
- Signing algorithm or key custody.

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [behavior] Given docs/examples/owner_conflict_interview.json sealed in interrogation mode with consent and training flags and written with --out-dir, when the operator runs --verify-package on the written JSON file, then the exit code is 0 and the output contains "ok": true and "hash_ok": true.  
  Verify: python3 -m cueliez docs/examples/owner_conflict_interview.json --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1 --out-dir /tmp/v --basename a && python3 -m cueliez --verify-package /tmp/v/a.json; echo $?
- **AC2** [behavior] Given the same exported file, when it is opened, then it still carries an export notice and an export time, or docs/schemas/sealed_package_v1.md states where each now lives.  
  Verify: grep -n export_notice /tmp/v/a.json; grep -n export docs/schemas/sealed_package_v1.md
- **AC3** [failure-path] Given the exported file with one observation's label edited, when --verify-package is run, then the exit code is non-zero and the output contains "hash_ok": false.  
  Verify: python3 -c "import json;p=json.load(open('/tmp/v/a.json'));p['observations'][0]['label']='x';json.dump(p,open('/tmp/v/b.json','w'))" && python3 -m cueliez --verify-package /tmp/v/b.json; echo $?
- **AC4** [failure-path] Given the exported file with gate_state.consent_attested_by changed, when --verify-package is run, then the exit code is non-zero and the output contains "hash_ok": false.  
  Verify: python3 -c "import json;p=json.load(open('/tmp/v/a.json'));p['gate_state']['consent_attested_by']='X';json.dump(p,open('/tmp/v/c.json','w'))" && python3 -m cueliez --verify-package /tmp/v/c.json; echo $?
- **AC5** [contract] Given the three owner transcripts docs/examples/owner_clean_interview.json, owner_conflict_interview.json, owner_hedging_interview.json, when each is sealed through the CLI and its exported JSON file is verified in a test, then all three verify, and the test fails if export adds any key that is not covered by the hash and not listed as excluded.  
  Verify: python -m pytest -q tests/ (the new test file is named in the DIARY.md entry that closes this request)
- **AC6** [docs] Given the change is merged, when docs/schemas/sealed_package_v1.md is read, then it lists exactly which top-level keys the package hash excludes and says the exported file verifies unchanged.  
  Verify: grep -n -i exclud docs/schemas/sealed_package_v1.md


**Open questions for product:**
- Engineering: does the fix change the hash definition? If yes, does schema_version change? Tell product the answer in DIARY.md before pilot materials describe the schema.

---

ENG REQUEST: ENG-002 Transcript ingest: reject unattributable or malformed input, flag and report empty turns

Date: 2026-11-11
**Why:** Today validate_transcript_turns accepts turns with no role, an unmappable role, or no text, and load_transcript falls back to the pre-validation path on any exception, so even a rejection would be swallowed. Observed 2026-11-11: [{"role":"subject"}] gives an empty-text turn; [5] gives {role:'',text:''}; {"foo":"bar"} gives []; a None turn is dropped so a 3-turn input is recorded with turn_count 2. For a sealed, auditable record the input must be reproducible and attribution must be reliable, so structural and attribution failures are rejected and benign empty turns are kept, flagged and counted. Full rationale in the DIARY.md entry of 2026-11-11.

**Decisions this follows:** AGENTS.md section 4 (admissibility, reproducible package); docs/OWNER_DECISIONS.md section 3 (artifacts attach to a case workflow)

**In scope:**
- Reject: a turn that is not an object or string; a turn whose role is missing or does not map to subject or interviewer; a wrapper with no recognised turn list; zero turns; a transcript where every turn has empty text.
- Keep and flag: a turn with a mapped role and empty or whitespace text, at its original position.
- Record an ingest report in the package, inside hash coverage.
- Remove the fallback in load_transcript that re-reads the input without validation after a failure.
- Stable error codes, documented.

**Out of scope:**
- Any threshold on the share of empty turns in v1.
- Changes to the role alias tables.
- Observer changes beyond not treating flagged-empty turns as statements.
- Mechanism and exception class: engineering decides, but codes must be stable and listed in docs/GATE_ERROR_CODES.md.

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [failure-path] Given a transcript file containing [5], when the CLI is run on it, then the exit code is non-zero, the error code is ingest_invalid_turn, the message names turn index 0, and no package or export file is written.  
  Verify: echo '[5]' > /tmp/t.json; python3 -m cueliez /tmp/t.json --out-dir /tmp/o; echo $?; ls /tmp/o
- **AC2** [failure-path] Given turns [{"role":"zzz","text":"hi"}] and separately [{"text":"hi"}], when each is ingested through the CLI, then both exit non-zero with error code ingest_unattributed_turn, and the message names the turn index and the original label if one was given.  
  Verify: python3 -m cueliez /tmp/t2.json --out-dir /tmp/o; echo $?
- **AC3** [failure-path] Given {"foo":"bar"}, [], and a transcript whose turns all have empty text, when each is ingested through the CLI, then each exits non-zero with ingest_unrecognised_structure or ingest_empty_transcript, and no package is written.  
  Verify: python3 -m cueliez /tmp/t3.json --out-dir /tmp/o; echo $?; ls /tmp/o
- **AC4** [behavior] Given the owner conflict transcript with one extra turn {"role":"subject","text":"  "} inserted between existing turns, when it is ingested and sealed, then it is accepted, the turn stays at its position, and source_artifact.ingest_report lists input_turn_count, accepted_turn_count and the index of the turn with code empty_text.  
  Verify: python3 -m cueliez /tmp/t4.json --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1 --out-dir /tmp/o --basename d && grep -n -A8 ingest_report /tmp/o/d.json
- **AC5** [behavior] Given the package from AC4, when the ingest_report is edited and --verify-package is run, then verification fails with hash_ok false, which shows the report is covered by the package hash.  
  Verify: python3 -m cueliez --verify-package /tmp/o/d.json (after editing ingest_report)
- **AC6** [behavior] Given the package from AC4, when its cues are listed with --show-cues, then no cue quotes or cites the empty turn as source text.  
  Verify: python3 -m cueliez /tmp/t4.json --show-cues --no-seal
- **AC7** [failure-path] Given a Python call load_transcript([5]), when it is executed, then it raises ValueError instead of returning a list.  
  Verify: PYTHONPATH=src python3 -c 'from cueliez.ingest import load_transcript; load_transcript([5])'
- **AC8** [contract] Given an input list of three turns, one of which is JSON null, when it is ingested, then ingest rejects it with ingest_invalid_turn and never reports a turn_count lower than the number of input turns.  
  Verify: PYTHONPATH=src python3 -c 'from cueliez.ingest import build_ingested_package as b; b([{"role":"subject","text":"a"},None,{"role":"subject","text":"b"}])'
- **AC9** [contract] Given all existing owner, vendor-alias and redteam fixtures, when the full test suite runs, then every existing ingest and fixture test still passes.  
  Verify: python -m pytest -q tests/test_ingest_vendor_normalization_kilo.py tests/test_ingest_phase7_iceman.py tests/test_fixtures_golden.py
- **AC10** [docs] Given the change is merged, when docs/TRANSCRIPT_INGEST_CONTRACT.md and docs/GATE_ERROR_CODES.md are read, then they list each new error code, the empty_text flag, and the ingest_report fields.  
  Verify: grep -n -E 'ingest_invalid_turn|ingest_unattributed_turn|ingest_empty_transcript|empty_text|ingest_report' docs/TRANSCRIPT_INGEST_CONTRACT.md docs/GATE_ERROR_CODES.md


**Open questions for product:**
- Engineering: a text-less turn that carries timing or audio-feature metadata (a silence segment) should keep that metadata for the pause and latency observers and still be flagged empty_text. Confirm this is feasible, or say what it breaks.
- Engineering: if ENG-001 changes hash coverage rules, state how ingest_report is covered.

---

ENG REQUEST: ENG-003 Sealed package records a hash of the original input, not only of the normalised transcript

Date: 2026-11-11
**Why:** source_artifact.transcript_sha256 is computed over the normalised transcript, so a reviewer cannot confirm that the package came from a specific exported file. For a package attached as an original artifact, the link to the exact input bytes is what lets a third party reproduce the run. Depends on ENG-001 and ENG-002.

**Decisions this follows:** AGENTS.md section 4 (reproducible, self-contained package); docs/TRANSCRIPT_INGEST_CONTRACT.md (source_artifact is non-finding metadata)

**In scope:**
- Add the SHA-256 of the raw input bytes to source_artifact for file and stdin input.
- Keep transcript_sha256 for the normalised form.
- Both values inside hash coverage.

**Out of scope:**
- Storing the raw transcript inside the package.
- Any change to export formats.

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [behavior] Given docs/examples/owner_clean_interview.json sealed from a file path, when source_artifact.source_sha256 is read, then it equals the sha256sum of that file.  
  Verify: sha256sum docs/examples/owner_clean_interview.json; grep -n source_sha256 /tmp/o/e.json
- **AC2** [behavior] Given the same transcript piped on stdin with the transcript argument set to -, when the package is sealed, then source_sha256 equals the sha256sum of the bytes piped in.  
  Verify: cat docs/examples/owner_clean_interview.json | tee /tmp/in.json | python3 -m cueliez - --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1 --out-dir /tmp/o --basename f; sha256sum /tmp/in.json
- **AC3** [failure-path] Given a sealed package whose source_sha256 value is edited, when --verify-package is run, then the exit code is non-zero and the output contains "hash_ok": false.  
  Verify: python3 -m cueliez --verify-package /tmp/o/e.json (after editing)
- **AC4** [docs] Given the change is merged, when docs/TRANSCRIPT_INGEST_CONTRACT.md is read, then the source_artifact example shows both hashes and says which input each covers.  
  Verify: grep -n -E 'source_sha256|transcript_sha256' docs/TRANSCRIPT_INGEST_CONTRACT.md

---

ENG REQUEST: ENG-004 Retention module: no built-in retention periods; wire it to operator input or remove it

Date: 2026-11-11
**Why:** src/cueliez/retention.py defines default retention windows of 3, 5 and 7 years by mode and derives retain_until from them. No source for those numbers is recorded, no CLI, session or export path imports the module, and it has no tests. Retention periods are legal and agency policy, and the deployment doc already assigns them to the operator. A shipped default reads as product guidance on a legal question.

**Decisions this follows:** docs/OWNER_DECISIONS.md section 3 (deploy posture, operator custody); docs/deployment/READINESS.md (operator responsibilities); GAMUT.md definition of done items 2 and 3

**In scope:**
- Remove built-in default durations from src/.
- Either wire retention so it only reflects a period the operator supplies, with tests and CLI help, or delete the unreferenced module.

**Out of scope:**
- Choosing legal retention periods for any jurisdiction.
- Encryption at rest or secure deletion (roadmap 9.8, later).

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [contract] Given the repository after the change, when src/ is searched for numeric retention durations, then there are no matches.  
  Verify: grep -rnE '365 ?\* ?24' src/ ; echo $?  (expect no output, exit 1)
- **AC2** [behavior] Given a default CLI run with no retention input, when the sealed JSON is inspected, then it contains no retain_until or other expiry date.  
  Verify: python3 -m cueliez docs/examples/owner_clean_interview.json --no-seal --print-json | grep -c retain_until
- **AC3** [contract] Given retention is kept in the product, when python -m cueliez --help is read and the module is searched for importers, then help names the operator-supplied retention input and at least one test in tests/ exercises it; if the module was removed, no source or doc refers to it.  
  Verify: python3 -m cueliez --help | grep -i retention; grep -rn retention tests/ src/
- **AC4** [docs] Given the change is merged, when docs/deployment/READINESS.md is read, then it states retention periods are set by the operator and the product ships none.  
  Verify: grep -n -i retention docs/deployment/READINESS.md

---

ENG REQUEST: ENG-005 Pilot metrics report command (latency, package completeness, gate outcomes)

Date: 2026-11-11
**Why:** docs/PILOT_VALIDATION_METRICS.md defines latency p50/p95, package completeness and gate compliance as the first-pilot measures, but scripts/ and the CLI have no command that produces them, so every pilot number would be hand-collected. Depends on ENG-001 (exported packages must verify). The report must be operational only; no accuracy, detection or credibility measure may appear.

**Decisions this follows:** docs/PILOT_VALIDATION_METRICS.md (reporting guardrails); docs/OWNER_DECISIONS.md section 2 (pilot success is non-accuracy)

**In scope:**
- A command that takes a directory of transcripts and gate flags, runs each through the real CLI path, and writes a JSON and a Markdown report.
- Report: per-run wall-clock, p50 and p95, package completeness per package using the existing completeness check, count of runs blocked by a gate error and the error codes.

**Out of scope:**
- Over-cue and cue-utility labels (human review, recorded in docs/demo/VALIDATION_NOTES.md).
- Any metric about deception, truthfulness, credibility, confessions or outcomes.
- Where the command lives (CLI flag or script): engineering decides.

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [behavior] Given the three docs/examples/owner_*.json transcripts in one directory and the gate flags --mode interrogation --consent --consent-attester OFFICER-001 --training-ack --training-version v1, when the report command is run on that directory, then it writes a JSON report with one entry per transcript containing wall_clock_ms, sealed true or false, and a completeness result, plus p50_ms and p95_ms for the set.  
  Verify: run the command on /tmp/owner_set (copies of the three files); python3 -c 'import json;print(json.load(open("/tmp/owner_set_report.json")).keys())'
- **AC2** [failure-path] Given the same directory and no consent flag in interrogation mode, when the report command is run, then every run is listed as blocked with error code consent_required, no package files are written, and the report states 0 sealed.  
  Verify: run the command without --consent; ls the output directory; grep -c consent_required on the report
- **AC3** [failure-path] Given the JSON and Markdown reports from AC1, when their keys and headings are searched for accuracy, detect, truth, credib, confession, or lie, then there are no matches, and a test in tests/ fails if such a key is added.  
  Verify: grep -i -E 'accura|detect|truth|credib|confess|\blie' /tmp/owner_set_report.json /tmp/owner_set_report.md ; python -m pytest -q tests/
- **AC4** [contract] Given a package that fails verification (hash edited), when it is included in the run set, then the report lists that package as failing integrity and the command exits non-zero.  
  Verify: python -m pytest -q tests/ (regression named in the DIARY.md entry that closes this request); the command's exit code is non-zero when a package fails verification
- **AC5** [docs] Given the command exists, when docs/PILOT_VALIDATION_METRICS.md and docs/demo/OPERATOR_DRY_RUN.md are read, then both give the exact command line and say the report is operational only and not a measure of the interview subject.  
  Verify: grep -n -i 'operational' docs/PILOT_VALIDATION_METRICS.md docs/demo/OPERATOR_DRY_RUN.md

### G. Response to the MediaMan entry (2026-11-11)

- Dashboard escaping request: accepted. Priority 1 with ENG-001, owner lead dev, written up as ENG-006 below.
- The two code commits MediaMan made to `src/` (`6a12c08`, `0f0e278`) are engineering's to review; I take no position on them beyond noting the full check set was not run on them.
- Training media: hold external use. The entry says no language-rule scan was done on captions, audio or filenames for any video, audio was transcribed for gov only, and scripts are not verbatim from `docs/demo/DEMO_SCENARIOS.md`. Messaging is mine. Before any video is shown outside the team I will scan its script and captions against `docs/LANGUAGE_RULES.md`; I need the script and caption files for that, not only the mp4s.

Process note: my first push of this entry was made from a clone taken before `220bc69` landed and overwrote that entry. I restored it in `75541c4` (the file differs from `220bc69` by my entry only, verified by diff). I now re-read the remote file immediately before each write.

ENG REQUEST: ENG-006 Officer dashboard and HTML outputs must render cue and transcript text as text, not markup

Date: 2026-11-11
**Why:** Raised by MediaMan (DIARY.md 2026-11-11): src/cueliez/delivery/dashboard.py inserts cue text into the page through innerHTML without escaping. Cue text, source quotes and officer notes come from transcripts, which are untrusted input, and the page is shown to an officer in a browser. A transcript containing markup would run in the officer's session, and an evidence tool whose display can be altered by the material it analyses cannot be relied on for a record. Product decision: priority 1, same tier as ENG-001, owned by the lead dev. I have not checked the other HTML surfaces myself; AC3 asks engineering to check and fix.

**Decisions this follows:** AGENTS.md section 4 (reproducible, self-contained package); AGENTS.md section 5 (delivery layer surfaces cues to the officer)

**In scope:**
- Escape every transcript-derived and officer-entered string in the dashboard page: message, cue_id, category, source quote text, officer note text.
- Check the officer HTML surface in src/cueliez/delivery/onscreen.py and the exported *.summary.html for the same property, and fix any that fail.
- Regression tests.

**Out of scope:**
- Authentication, TLS and CSRF hardening of the dashboard (roadmap 9.8).
- Visual redesign.

**Acceptance criteria (each is observable and has a stated check):**

- **AC1** [failure-path] Given LiveDashboardServer running and a cue pushed whose message and whose source_quotes[].text both equal `<img src=x onerror=alert(1)>`, when the dashboard page is loaded and the cue list renders, then the string appears on screen as literal characters, the DOM contains no img element with src x, and no dialog opens.  
  Verify: python -m pytest -q tests/test_dashboard.py (new test named in the DIARY.md entry that closes this request)
- **AC2** [failure-path] Given cue fields cue_id, category, message, source quote text and an officer note each set to `<b>x</b>`, when each is rendered by the dashboard, then the rendered output contains &lt;b&gt;x&lt;/b&gt; for each field and no raw <b> element.  
  Verify: python -m pytest -q tests/test_dashboard.py tests/test_delivery.py
- **AC3** [failure-path] Given a transcript whose subject turn text is `<script>alert(1)</script>` sealed through the CLI with --format html, when the exported summary HTML and the onscreen officer HTML are produced, then neither file contains an unescaped script tag and both show the text as literal characters.  
  Verify: python3 -m cueliez /tmp/xss.json --mode generic --out-dir /tmp/o --basename x --format html && grep -c '<script>alert' /tmp/o/x.summary.html  (expect 0)
- **AC4** [behavior] Given the existing owner transcripts and dashboard tests, when the full suite runs, then all existing dashboard, delivery and export tests still pass and cue text displays unchanged for ordinary text.  
  Verify: python -m pytest -q tests/test_dashboard.py tests/test_delivery.py tests/test_export.py

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
