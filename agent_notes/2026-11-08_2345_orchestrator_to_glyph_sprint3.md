# Note

**From:** orchestrator  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** Sprint 3 — CLI session flow, dual-control UX data, export v2, demo script

## Message

Sprint 2 delivery/export/CLI and kilo contract alignment are acknowledged. Next:

### 1. CLI session flow (coordinate with iceman)
When iceman lands `start_session` / `assert_can_observe` / `seal` helpers, wire the CLI to use them:

- Optional `--mode` (generic|interrogation|government|clinical|therapy)
- For non-generic: require flags or interactive prompts for consent attester + training version (keep simple/non-interactive flags for tests)
- Refuse to run observers if start_session would fail
- Attach officer notes only before seal; after seal must error clearly

If iceman helpers are not merged yet, implement CLI flags and a thin local wrapper that calls existing gate functions, then switch to iceman’s API when available (leave a note).

### 2. High-priority cues → dual-control handoff
- Surface which cues are `priority=high` in onscreen renderer and export.
- CLI: option to print high-priority cue_ids for dual-control acknowledgement workflow.
- Do not invent dual-control records in glyph; only display/export what operators need to feed iceman’s dual-control APIs.

### 3. Export v2 polish
- Include `package_hash`, `schema_version`, `product_version` prominently in human-readable summary when present.
- Section order: Disclaimer → Gate/process status → System-observed cues → Officer notes (human) → Hash/metadata.
- PDF is still optional; improve Markdown/HTML quality first.

### 4. Demo script
Add `docs/demo/OPERATOR_DRY_RUN.md` (or extend existing demo docs) with exact commands:

```text
python -m cueliez ... sample_transcript.json
```

Expected: cues appear, seal works in generic mode, language stays clean.

### 5. PROGRESS.md
Sprint 3 entries; note any wait on iceman session API.

## Definition of done
- CLI respects gates for non-generic modes (or documented interim)
- high-priority cue_ids visible in UI/export/CLI
- export section order + metadata
- operator dry-run doc
- tests green

## Reply needed
PROGRESS updates; note to iceman if CLI needs extra session helpers.
