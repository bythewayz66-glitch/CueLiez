# Phase 4 Design Notes — Gated Modalities & Audio-Only Real-Time Path (Kilo)

**Status:** design notes only (first-pilot scope `generic` + `interrogation`).  
**Defaults:** prosody/visual/physiological feature observers are **off by default** (not in `default_runner()`; `full_runner()` only emits when required feature metadata is present). No new modalities enabled by default.

## Consent, jurisdiction, and policy checks (required before capture/extraction)
Before enabling any non-text modality, the deployment must satisfy applicable law, policy, and CueLiez gate requirements:

- **Audio feature extraction (prosody, speech rate, latency, pauses):** obtain required consent/notice; confirm jurisdictional rules for recording/analysis; document purpose limitation and retention; apply role-appropriate gate state (`consent`, `training`, `intended_uses`) before observation/seal. Prefer on-device/on-prem processing; do not transmit raw audio to public services for production implementation.
- **Camera/video-derived features (gaze, blink, motor activity proxies):** require explicit consent/policy authorization; confirm surveillance/recording legality and workplace/subject notice requirements; restrict to authorized contexts only. Never covert. Feature extraction should produce minimal derived indicators (not identity/biometric identification claims).
- **Wearables/physiological inputs (heart rate, HRV, electrodermal summaries):** require explicit informed consent; confirm medical/privacy/jurisdiction constraints; treat as sensitive data with strict minimization, access control, and retention limits. Do not present as medical diagnosis or clinical device output.

All modality outputs, if ever enabled, must remain **probabilistic observations/cues** with neutral labels, confidence scores, model/method IDs, evidence, and the standard epistemic/disclaimer controls. No deception, credibility, guilt, intent, or diagnostic findings.

## Prioritized path (design): audio-only real-time indicators
If/when enabled under proper controls, prioritize **audio-only, derived-feature** indicators (lowest additional modality burden compared to video/wearables):
1. **Response latency** (already supported from timestamps/metadata when provided).
2. **Speech rate / speaking-time shifts** (requires duration/word-timing metadata or on-prem feature extraction).
3. **Pause patterns** (requires pause/silence metadata or on-prem VAD/diarization features).
4. **Prosody variability/stress-feature proxies** (derived acoustic features only; requires explicit gating and validation).

Implementation notes (future): use on-prem/private-cloud pipelines; pass only derived features/metadata into observers; preserve seal/hash/audit integrity; add modality-specific consent records and tests before enabling in packs or production flows.
