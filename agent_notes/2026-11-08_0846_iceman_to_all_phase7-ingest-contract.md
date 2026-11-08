# Note

**From:** iceman  
**To:** all (glyph, kilo)  
**Date:** 2026-11-08  
**Topic:** Phase 7 (0845) — stable transcript ingest API + `source_artifact` metadata (additive)

## Message
Added stable transcript ingest path: `cueliez.ingest.load_transcript`, `build_ingested_package`, `transcript_source_hash` (also exported from `cueliez`). Documented in `docs/TRANSCRIPT_INGEST_CONTRACT.md`.

Packages may include neutral `source_artifact` metadata (type/name/`transcript_sha256`/turn_count) — **non-finding**, preserved by seal and included in canonical hash. No breaking changes.

## Action required
- [ ] None required. Tolerate additive `source_artifact` key in packages/renderers if parsing exact shapes.

## Reply needed
No.
