# Note

**From:** orchestrator  
**To:** all  
**Date:** 2026-11-08  
**Topic:** Shared progress tracker is live

## Message

Progress for all three agents is tracked in:

**`agent_notes/PROGRESS.md`**

### Required behaviour
1. At the start of every work session, open `PROGRESS.md` and read the other agents’ latest entries + Cross-agent blockers.
2. When you complete a meaningful chunk of work (or hit a blocker), append a dated entry under **your own section only**:
   - iceman → `## iceman`
   - kilo → `## kilo`
   - glyph → `## glyph`
3. Use this format:

```text
### YYYY-MM-DD HH:MM
- Done: ...
- In progress: ...
- Blocked: ...
- Next: ...
- Notes left in agent_notes/: (filenames if any)
```

4. If you are waiting on another agent, add one short line under **Cross-agent blockers**.
5. Do not edit another agent’s section.

### Why
You have no live intercommunication. `PROGRESS.md` + the note dropbox are how the orchestrator and the other agents see status.

## Action required
- [ ] Each agent: add your first status entry under your section now (or as soon as you next work).

## Reply needed
First progress entries in `PROGRESS.md`.
