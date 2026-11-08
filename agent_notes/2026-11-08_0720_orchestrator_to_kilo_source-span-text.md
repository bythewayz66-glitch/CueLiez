# Note

**From:** orchestrator  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** Observations must carry the actual words that triggered them — not only turn ids

## Message

Owner review of CLI output: packages/cues show turn ids but **not the subject/officer text** that caused the observation. For human review and admissibility-friendly inspection, that is insufficient.

### Requirement
Every observation that is turn-anchored should include in `evidence` (and remain seal-compatible):

- `turn_index` (existing)
- **`source_text`** (or `span_text`): the exact turn text(s) used
- When the signal spans multiple turns (e.g. claim conflict): `source_texts` list and/or `turn_indices` with paired quotes
- Optional but preferred: `speaker` / `role` for each span

Rules:
- Quote the transcript; do not paraphrase into a verdict.
- Truncate only if extremely long (document max length, e.g. 500 chars with ellipsis) — prefer full short turns.
- Neutral labels and language rules still apply; source text is evidence, not a finding.
- Deterministic `cue_id` scheme can stay as-is.

### Scope
Prioritize high-value observers first:
1. Claim conflict / timeline / detail drift / location divergence
2. Hedging, vagueness, pronoun distancing, certainty swing
3. Evasion, latency, answer-length (include the response text that was measured)

### Tests
- Fixture runs assert `source_text` or `source_texts` present when `turn_index` is present
- No forbidden labels introduced

### Contract note
Update glyph (and iceman if needed) via `agent_notes/` on the evidence field names you standardize on (`source_text` preferred).

## Action required
Implement evidence fields + tests; leave contract note for glyph.

## Reply needed
PROGRESS entry + note to glyph.
