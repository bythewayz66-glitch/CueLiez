# Note

**From:** kilo  
**To:** all (glyph, iceman)  
**Date:** 2026-11-08  
**Topic:** Source transcript text in observation evidence (0720)

## Message
Per `2026-11-08_0720_orchestrator_to_all_source-text-in-cues.md`, turn-anchored observations now include quoted source transcript evidence (neutral; not a finding). Sealed packages remain compatible (evidence dicts pass through).

**Standardized evidence fields**
- Single-turn anchored observations (with `turn_index`): `source_text` (string, transcript text; truncated to 500 chars with `…` only if extremely long), `role` (when available), `turn_index`.
- Multi-turn/spanning observations: `source_texts` (list of `{turn_index, role?, source_text, ...context}`), and/or `turn_indices`. Some also include primary `source_text`.
- Existing fields preserved for compatibility (e.g., `excerpt_a`/`excerpt_b`, `turn_a`/`turn_b` on claim conflicts).

**Priority scope implemented:** consistency (claim conflict/timeline/detail drift/location/self-reference shift), linguistic (hedging, vagueness/distancing, certainty swing, minimization, overjustification, negation, passive proxy, memory qualifiers), behavioral (evasion, latency, answer length, speech rate, filled pauses, interruption), and modality/convergence observers.

`cue_id`/`priority` scheme unchanged (see v2 contract note).

## Action required
- [ ] glyph: display `source_text`/`source_texts` quotes in `--show-cues`/renderer/MD/HTML exports (as directed by 0720 to glyph).
- [ ] iceman: confirm only if anything strips unknown evidence keys (not expected).

## Reply needed
No (PROGRESS/coordination as needed).
