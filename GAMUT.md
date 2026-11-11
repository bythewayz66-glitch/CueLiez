# GAMUT.md — Project Rules for CueLiez

Read this and `AGENTS.md` before touching anything. `AGENTS.md` holds the product, language, seal and gate rules. This file holds how the team works. If the two ever conflict, the more restrictive rule wins.

## Roles

- **Lead project dev** owns the code: correctness, integration, tests, CI, repo hygiene. Nothing reaches the owner for review until it works.
- **Product manager** owns the product: scope, priorities, positioning, roadmap (`TODO.md` phases), pilot and market decisions.
- Neither role overrides the other. Engineering raises scope questions to product; product raises feasibility questions to engineering. Product decisions that change behaviour are written down before code changes. Nobody edits the other's deliverables without telling them.

## Definition of done

A change is done only when all of these are true:

1. It is implemented for real. No stubs, placeholders, TODO/FIXME markers, `NotImplementedError`, fake return values, or hard-coded results standing in for logic.
2. It is integrated. It is reachable from the CLI, session, export or delivery path it belongs to, not just defined.
3. It is tested, and the tests exercise the real behaviour, including failure paths. Fail-closed behaviour in gates is tested as fail-closed.
4. The full check set below passes, run and observed, not assumed.
5. Docs, CLI help and schema references match what the code now does.
6. A `DIARY.md` entry records what changed and what was verified.

A feature that is hard is finished, not removed. A bug is fixed, not hidden behind a guard, a broad `except`, or a relaxed test.

## Honesty rules

- Do not claim something works until it has been run. Report results as observed, including failures.
- Do not mark a `TODO.md` item `[x]` unless it is implemented and tested. Docs-only or operator-dependent items are labelled as such.
- Read the existing code before editing it or assigning work on it.
- Do not invent product behaviour. If a requirement is unclear, ask.

## Code style

- No explanatory notes in code. A comment is allowed only for a non-obvious reason (a hidden constraint or a workaround), in one short line. History, status and reasoning go in `DIARY.md`.
- Runtime dependencies stay at zero unless a dependency is actually imported and needed. Python 3.10+ compatibility is required (CI matrix is 3.10 to 3.13).
- Follow the language and epistemic rules in `AGENTS.md` and `docs/LANGUAGE_RULES.md` in every string, comment, doc and test fixture. Observation and cues only.
- Keep changes to the scope asked for, but prefer a complete sprint of related work over scattered small edits.

## Checks (all must pass before handoff)

Run from the repo root with `src` on the path or the package installed:

```
python scripts/check_no_fake_code.py
python scripts/check_no_tracked_artifacts.py
python scripts/check_version_consistency.py
python -m cueliez --help
python scripts/check_cli_contract.py
python scripts/check_contracts_phase9.py
python -m pytest -q
```

These mirror `.github/workflows/ci.yml`. Do not commit `.venv`, `uv.lock`, `build/`, `dist/`, `*.egg-info` or bytecode.

## Notes and communication

- Notes, decisions, findings and session logs go in `DIARY.md` at the repo root, newest entry first, each dated and short.
- `agent_notes/` is the legacy inter-agent dropbox. New work records go in `DIARY.md`.
- No secrets, credentials or personal data in the repo, diary or notes.

## Handoff to the owner

A handoff states: what changed, which checks were run and their results, what is still open, and any product question that needs the product manager. Anything unfinished is listed as unfinished, never presented as done.
