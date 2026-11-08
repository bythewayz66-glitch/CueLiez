# agent_notes — Private Agent Dropbox

This directory is the **only** approved channel for iceman, kilo, and glyph to pass notes to each other.

There is no live intercommunication profile. Agents do not talk directly. They leave written notes here and check for new notes from the others.

---

## How to use

### Writing a note
1. Create a new Markdown file with this naming pattern:

   ```
   YYYY-MM-DD_HHMM_<from>_to_<to>_<short-topic>.md
   ```

   Examples:
   - `2026-11-08_1430_iceman_to_kilo_observation-schema.md`
   - `2026-11-08_1515_kilo_to_glyph_cue-fields.md`
   - `2026-11-08_1600_glyph_to_iceman_officer-notes-field.md`
   - `2026-11-08_1620_kilo_to_all_runner-output-shape.md`  (use `all` when the note is for both other agents)

2. Keep the note short, factual, and actionable.
3. State clearly:
   - What you need / what you are providing
   - Any schema or field names involved
   - Whether a reply is required

### Reading notes
- At the start of every work session, and periodically while working, list the files in this directory.
- Read any notes addressed to you (`_to_iceman_`, `_to_kilo_`, `_to_glyph_`, or `_to_all_`).
- After you have acted on a note (or decided no action is needed), you may reply with a new note or add a short “acknowledged” note.

### Rules
- Do **not** put secrets, credentials, or personal data in notes.
- Do **not** use this channel for long design debates — keep notes tight.
- Prefer one clear request or one clear status update per file.
- When a note is fully resolved, the author or the recipient may delete it (or move it to `agent_notes/archive/` if you create that folder).
- Still obey `AGENTS.md` and language rules in any text you write here.

---

## Suggested note template

```markdown
# Note

**From:** iceman  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** observation schema – confidence.model_id

## Message
Please ensure every observer emits a non-empty confidence.model_id.  
Seal validation will reject packages that are missing it.

## Action required
- [ ] Confirm current observers already do this
- [ ] Or update them and reply with status

## Reply needed
Yes — short status when done.
```

---

## Ownership
- iceman, kilo, and glyph may all read and write in this directory.
- No other agents should use it unless explicitly instructed.
