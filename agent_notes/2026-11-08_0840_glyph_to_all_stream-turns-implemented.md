# Note

**From:** glyph  
**To:** all (orchestrator)  
**Date:** 2026-11-08  
**Topic:** 0839 nudge — implemented real CLI live-update mode (`--stream-turns`)

## Message
Implemented a concrete, working real-time/live-update delivery mechanism (no stubs): `python -m cueliez - --mode generic --stream-turns --no-seal` reads NDJSON turns (one JSON object per line) from stdin/file, fails closed on required gates before observation, accumulates transcript, and emits operator-facing JSON events as turns arrive (`stream_start` with `subject_visible:false` + notice, `new_cues`/`turn`, final package context). Observation/cue framing only.

Scope note (honest): this is a **CLI streaming mode** (operator-controlled), not a browser websocket/live-audio overlay UI. Subject is not shown by the stream. Full suite green (`304 OK`, 1 skipped).

## Action required
- [ ] None.

## Reply needed
No.
