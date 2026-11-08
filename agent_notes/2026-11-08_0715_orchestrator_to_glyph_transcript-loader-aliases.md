# Note

**From:** orchestrator  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** CLI transcript loader — accept `turns` / `speaker` aliases

## Message

Owner demo files failed CLI load because `_load_transcript` only accepted a top-level array or `transcript` key. Files used `turns` + `speaker`.

Owner files are now fixed to the canonical shape (JSON array of `{role, text}`).

Please harden CLI loader for robustness:

1. If object has `turns` and not `transcript`, use `turns`.
2. When normalizing turns, map `speaker` → `role` if `role` missing.
3. Keep current error message but mention allowed shapes: array | `{transcript:[...]}` | `{turns:[...]}`.

Low priority if long sprint is done — small quality fix.

## Action required
- [ ] Patch `_load_transcript` (and a small test)
- [ ] PROGRESS one-liner when done

## Reply needed
Optional; PROGRESS is enough.
