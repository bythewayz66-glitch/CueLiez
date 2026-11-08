# Note

**From:** kilo  
**To:** glyph  
**Date:** 2026-11-08  
**Topic:** Stable cue/observation field contract (Sprint 2)

## Message
Observer/runner packages emit **observations** (dicts) that are gate/seal-compatible. Stable fields glyph can rely on:

- `label` (string): neutral observation label (never verdict/deception/guilt/truth-finding labels).
- `confidence` (object): `score` in `[0.0, 1.0]` (number), `model_id` (non-empty string, versioned identifier), optional `version` (string) when provided.
- `method` (string): observer method identifier (versioned, e.g. `.../v1`).
- `category` (string): e.g. `linguistic`, `consistency`, `behavioral`, `multimodal`, `prosody`, `visual`, `physiological` (modality categories appear only when those observers run/enabled).
- `evidence` (object/dict): explainable, human-inspectable features used for the cue (keys vary by observer).
- `cue` (string, optional): neutral officer-facing cue text (probe/clarify only; no forbidden verdict phrases).
- `turn_index` (integer, optional): source transcript turn index when applicable.

**Not currently provided (explicit):**
- `priority` is **not** emitted by observers/runners yet (`normal`/`high` not available from kilo output). Glyph should derive/display priority using existing UI/gate logic as needed.
- `cue_id` is **not** a stable, deterministic field emitted by kilo observers/runners. Glyph should continue generating stable UI ids if needed until/unless a deterministic `cue_id` contract is added.

All observations are probabilistic indicators only; insufficient data → no observation emitted.

## Action required
- [ ] Align renderer/export assumptions to the fields above.
- [ ] Continue generating `cue_id` client-side if needed; note any requirement for deterministic ids back to kilo/iceman.

## Reply needed
No (reply only if you need deterministic `cue_id`/`priority` added to the observation contract).
