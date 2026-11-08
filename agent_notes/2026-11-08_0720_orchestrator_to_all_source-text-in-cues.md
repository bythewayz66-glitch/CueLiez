# Note

**From:** orchestrator  
**To:** all  
**Date:** 2026-11-08  
**Topic:** Source transcript text must appear with observations/cues

## Message

Owner review: turn ids alone are not enough. Reviewers need the **actual words** that supported each observation.

- **kilo:** put `source_text` / `source_texts` (and role if available) in observation evidence — see `2026-11-08_0720_orchestrator_to_kilo_source-span-text.md`
- **glyph:** show those quotes in `--show-cues`, onscreen renderer, and MD/HTML export — see `2026-11-08_0720_orchestrator_to_glyph_show-source-text.md`
- **iceman:** no seal change expected; ensure evidence dicts are not stripped at seal time (they should already pass through if part of observation objects). Confirm only if something strips unknown evidence keys.

This is the current priority over new features.
