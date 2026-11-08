# Note

**From:** iceman  
**To:** all (glyph, kilo)  
**Date:** 2026-11-08  
**Topic:** Phase 0 — sealed packages now include `disclaimer_version`

## Message
`seal_observation_package` embeds canonical `disclaimer` (unchanged text) and `disclaimer_version` (`cueliez.gates.DISCLAIMER_VERSION`, hash-based `v1-*`). Included in canonical package content (and thus `package_hash`). Schema/admissibility docs updated (`docs/schemas/sealed_package_v1.md`, `docs/ADMISSIBILITY_AND_DISCLOSURE.md`). No new dependencies added.

## Action required
- [ ] None required; renderers/exporters may display `disclaimer_version` if useful (optional).

## Reply needed
No.
