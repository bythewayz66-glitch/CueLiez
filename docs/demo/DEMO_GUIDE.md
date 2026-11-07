# CueLiez Demo Guide

## Goal
Show how CueLiez helps a professional run a clearer, better-documented interview by surfacing **observations and cues** — while enforcing **consent/gates** and never producing verdicts.

## Audience mapping
| Audience | Pack | Emphasize | Avoid |
|---|---|---|---|
| Government / high-security | `gov` | authority/scope context, consistency/timeline cues, dual-control, auditable records | clearance/security findings, automated decisions |
| Legal / investigative | `leg` | testimony specificity/conflicts, neutral follow-up questions, documentation | guilt/innocence, evidentiary conclusions, detention/charging automation |
| Medical / clinical support | `med` | communication/history-taking clarity, gentle clarification cues | diagnosis, symptom validity, credibility judgments, medical-device claims |
| Therapy / supportive | `thrp` | pacing/clarification/support cues, non-adversarial framing | diagnosis, risk adjudication, credibility/truthfulness judgments |

## Recommended flow (15–25 min)

### 1. Frame it (1–2 min)
- “CueLiez is a Legal Interview Engine. It is **not a lie detector**.”
- “It observes signals and testimony patterns and gives the professional **cues** — prompts for human review.”
- “Humans judge. The system enforces gates and seals observed indicators, not verdicts.”

### 2. Show the problem (1–2 min)
- Interviews are high-stakes and cognitively demanding.
- Inconsistencies, vagueness, timing/response shifts, or deflection can be hard to track live.
- Goal: sharper questions and fairer, more auditable inquiry.

### 3. Run a safe scenario (4–6 min)
Use a synthetic transcript from `DEMO_SCENARIOS.md`.
```python
from cueliez.packs import get_pack
from cueliez.delivery import OnscreenCueRenderer

pack = get_pack("leg")  # choose for audience
pkg = pack.build_package(transcript, session_id="demo")
panel = OnscreenCueRenderer(show_evidence=True).render_panel(pkg["observations"], max_cues=6)
print(panel["text"])
```
Narrate: *“These are cues — for example, hedging/vagueness or a possible statement conflict. The professional decides how to follow up.”*

### 4. Show professional delivery (2–4 min)
- **Onscreen:** prioritized cue list, turn/category/score/evidence, “not findings” notice.
- **Audio:** priority tones + script/manifest for professional awareness (where appropriate).
```python
from cueliez.delivery import AudioCueRenderer
AudioCueRenderer(output_dir="demo_audio", allow_playback=False).render_panel(pkg["observations"], max_cues=5)
```
Explain: audio/onscreen cues support attention; they do not announce conclusions.

### 5. Show guardrails (3–5 min)
Pick what fits the audience:
- **Consent/training gates:** high-stakes modes require affirmative attested consent and training.
- **Government dual-control:** high-priority cues require dual acknowledgements before seal.
- **Seal hardening:** `observed_indicator`, grounded, disclaimer, `is_definitive_finding=false`; verdict labels/annotations rejected.
- **Prohibited uses:** no automated decisions, no diagnosis, no polygraph/lie-detector claims.

### 6. Close (1–2 min)
- “CueLiez helps professionals notice what to clarify and keeps an auditable record of observed indicators.”
- “It is designed for meaningful inquiry — not automated truth.”
- Ask: *“Which interview workflow would you want to evaluate first?”*

## Tips
- Keep one synthetic scenario loaded before the demo.
- If a live run produces no cues, explain thresholds/features and switch to the prepared scenario.
- Use the audience’s pack and language.
- If asked for a claim the product must not make, decline clearly and restate the compliant capability.
