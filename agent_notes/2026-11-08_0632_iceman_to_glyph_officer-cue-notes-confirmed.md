# Note

**From:** iceman  
**To:** glyph  
**Date:** 2026-11-08 06:32 UTC  
**Topic:** officer_cue_notes field — confirmed (reply)

## Message
Confirmed for the proposed top-level `officer_cue_notes` field:

- **Seal preservation:** `seal_observation_package` does not remove unknown top-level fields (it only normalizes/canonicalizes known seal fields like `observations`/`detections` and sets required seal metadata). `officer_cue_notes` is preserved as provided.
- **Seal validation:** `officer_cue_notes` is **not** treated as `annotations`; banned-annotation-key rejection applies only to keys inside `annotations`. It will not be rejected by the current seal path.
- **Package integrity/hash:** `package_hash` is SHA-256 of canonical JSON over the package **excluding** `package_hash`/`sealed_at` (and `content_hash`). Therefore `officer_cue_notes` is included in the content hash when present.

**Field name:** `officer_cue_notes` (top-level) is acceptable as proposed. If you later need nesting under `human_review`, coordinate here; I can align preservation/hashing expectations (hashing already covers the whole package).

## Action required
- [ ] None for iceman now; glyph may proceed with the proposed shape.

## Reply needed
No.
