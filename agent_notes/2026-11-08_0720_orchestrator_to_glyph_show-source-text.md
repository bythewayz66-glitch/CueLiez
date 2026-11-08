# Note

**From:** orchestrator  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** Surface source span text in cue UI, CLI --show-cues, and exports

## Message

Owner feedback: results show turn ids but not the **actual words** that triggered the observation. Humans need to see the quoted transcript span.

### Requirement
When observations/cues include evidence fields from kilo (`source_text`, `source_texts`, and/or turn-linked quotes):

1. **`--show-cues` / OnscreenCueRenderer** — under each cue, show:
   - turn id(s)
   - quoted source text (clearly labeled e.g. `Source:` or `Transcript:`)
2. **Export Markdown/HTML** — in the System-observed cues section, include the same quotes (not only ids).
3. **JSON** — already carries evidence if kilo adds it; do not strip evidence on export.

If kilo has not landed fields yet:
- Interim: when rendering, if you have access to the original transcript list in CLI, resolve `turn_index` → text and display it (CLI path can pass transcript into renderer).
- Prefer kilo’s evidence once present so sealed packages are self-contained without the original file.

Language: still observation/cue framing only. Quoting the subject is not a finding.

Also: keep the transcript loader alias work (`turns`/`speaker`) if not done.

## Action required
- [ ] Display source text in renderer + CLI
- [ ] Display source text in human-readable exports
- [ ] Tests for presence of quote when evidence/transcript available
- [ ] PROGRESS update

## Reply needed
PROGRESS entry; coordinate with kilo’s evidence field names.
