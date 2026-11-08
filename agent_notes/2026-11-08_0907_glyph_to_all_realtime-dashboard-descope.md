# Note

**From:** glyph  
**To:** all (orchestrator, owner-visible)  
**Date:** 2026-11-08  
**Topic:** 0906 task 8 — full browser websocket/live-audio dashboard descoped (no stubs)

## Message
**Descope (explicit, owner-visible):** a **full browser websocket + live-audio dashboard** (live audio ingest, websocket server, browser UI receiving real-time cues from audio streams) is **not implemented** in this repo. Per project rules, I did not add stubs, placeholders, fake endpoints, or simulated live audio behavior.

**What is implemented and real (glyph-owned):**
- `--stream-turns`: CLI live-update mode (NDJSON turns over stdin/file) emitting newly surfaced observation cues as turns arrive; `stream_start` reports `subject_visible:false`; gates enforced; observation-only notices.
- Officer HTML surface: low-distraction, turn-linked/glanceable, acknowledge/dismiss/note capture, explicit **Officer-only / subject not shown** notice, confidence/method provenance display.
- Exports/review: disclaimer-first, system-observed cues vs officer notes (human) separated, canonical JSON+hash as original artifact; RMS/case attachment documented (no live RMS connector).
- Latency: local text-path measurements documented (environment-specific; <1–2 s target met in local reference).

**Follow-up needed for full dashboard:** explicit scope + architecture (local/private-cloud web service, auth/session model, audio stream hook contract with consent/jurisdiction gates, websocket/SSE transport, browser officer UI, security/CJIS-aligned deployment controls, tests). Audio processing/stream hooks remain gated and off by default.

## Action required
- [ ] Owner/orchestrator: confirm priority/scope for full browser websocket+live-audio dashboard.

## Reply needed
Yes (if dashboard is required next).
