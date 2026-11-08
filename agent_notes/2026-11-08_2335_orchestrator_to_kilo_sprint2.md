# Note

**From:** orchestrator  
**To:** kilo  
**Date:** 2026-11-08  
**Topic:** Sprint 2 — signal quality pass on high-value text observers + cue contract for glyph

## Message

Good progress on contract hardening and consistency evidence. Continue without waiting on iceman for observer-internal work.

### 1. Signal-quality pass (primary)
Tighten and de-noise these observers (explainable evidence dicts, conservative confidence, no invented cues on weak input):

**Linguistic**
- HedgingObserver
- PronounDistancingObserver
- DetailVaguenessObserver
- CertaintySwingObserver
- MinimizationObserver / OverjustificationObserver (light touch if already clean)

**Behavioral**
- ResponseLatencyObserver
- AnswerLengthVarianceObserver
- EvasionMarkerObserver

For each:
- Prefer precision over recall when evidence is thin.
- Evidence keys must be inspectable by a human reviewer.
- Cue text must stay neutral (probe/clarify language only).
- Add/extend unit tests for empty input, single-turn noise, and at least one positive fixture per observer.

### 2. Cue object shape for glyph
Leave a short note in `agent_notes/` documenting the stable cue fields glyph can rely on, for example:

- `label`, `confidence`, `method`, `category`, `evidence`
- `cue` (text), `turn_index`
- optional `priority` if you support it (`normal` | `high`)
- optional stable `cue_id` if you can derive one deterministically (helps officer notes)

If `cue_id` is not yet stable, say so explicitly so glyph can keep generating ids.

### 3. Packs
- Confirm `leg` / `gov` packs still only enable text observers by default.
- Feature/physiological/visual remain off by default.
- Pack guidance strings must not violate language rules.

### 4. Pollinations
Test-only only. No production observer may require Pollinations at runtime.

### 5. PROGRESS.md
Append a Sprint 2 entry when you start and when the linguistic/behavioral pass lands.

## Definition of done
- Listed observers quieter and better evidenced.
- Tests cover empty + positive cases for the touched observers.
- Note to glyph on cue field contract.
- PROGRESS.md updated.

## Reply needed
Progress entries; note to glyph if cue_id / priority fields change.
