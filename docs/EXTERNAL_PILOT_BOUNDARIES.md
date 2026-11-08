# External Pilot Boundaries (government / clinical / therapy)

**Status:** Operational boundaries for scoping external pilots.  
**Rule:** Observation and cues only — never findings. First-pilot messaging remains **`generic` + `interrogation`** unless explicitly scoped and approved. See `AGENTS.md`, `docs/LANGUAGE_RULES.md`.

## Government mode
- **Gates:** requires affirmative consent (attester), training acknowledgement/version, and **dual-control acknowledgement** for high-priority cues before seal (`dual_control_incomplete` fail-closed). Prohibited uses blocked.
- **External pilot:** only when a specific partner demands it and scope/approvals are explicit; dual-control must remain enforced and auditable (`gate_state`/records preserved).
- **Messaging:** keep out of general pilot marketing/messaging unless explicitly scoped.

## Clinical / therapy packs and modes
- **Code status:** clinical/therapy modes and domain packs may exist in code; gate rules apply (consent + attester + training required for non-generic modes).
- **External pilot/messaging:** **out of pilot messaging unless explicitly scoped** and appropriate approvals/clinical governance are in place. Not a medical device; no diagnosis.
- **Use:** if ever scoped, use domain consent/training materials and maintain observation-only, non-diagnostic language.

## Gated modalities (audio/camera/wearable)
- Off by default. Enablement requires explicit consent + jurisdiction validation (`record_modality_consent` / `require_gated_modality` / `assert_can_observe(..., modalities=...)`) and policy approval where applicable.
