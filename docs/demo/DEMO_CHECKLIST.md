# CueLiez Demo Checklist

## Pre-demo (setup)

- [ ] **Audience/pack selected:** `gov` / `leg` / `med` / `thrp` chosen; talk track adjusted.
- [ ] **Compliant framing ready:** I can say “not a lie detector; observations/cues for human review.”
- [ ] **Safe data ready:** synthetic transcript(s) loaded/tested; no unauthorized sensitive data.
- [ ] **Environment ready:** repo/dependencies available; `PYTHONPATH=src` or installed package; demo output path writable.
- [ ] **Core demo tested:**
  - [ ] `get_pack(...).build_package(...)` runs
  - [ ] `OnscreenCueRenderer().render_panel(...)` displays cues
  - [ ] `AudioCueRenderer(..., allow_playback=False).render_panel(...)` generates assets (if showing audio)
- [ ] **Guardrail example ready:** consent/training gate, dual-control (gov), or seal hardening/prohibited-use rejection.
- [ ] **Q&A ready:** reviewed `DEMO_QA.md`, especially “lie detector?” and “can it tell if someone is lying?”.
- [ ] **Disclaimers accessible:** can point to `docs/compliance/DISCLAIMERS.md` or in-product disclaimer language.

## During demo

- [ ] Open with the **not-a-lie-detector** framing.
- [ ] Describe every output as an **observation/cue for professional review**.
- [ ] When showing a cue, mention **evidence/confidence + human follow-up**.
- [ ] Show at least one **guardrail** (gates/consent/seal/prohibited uses).
- [ ] Avoid domain-overclaiming (no legal findings, no diagnosis, no automated decisions).
- [ ] If asked an unsafe question, **decline the claim clearly** and restate compliant capability.
- [ ] Use audience-appropriate language and pack.

## Post-demo

- [ ] Share appropriate materials: `README`, `MISSION`, `LANGUAGE_RULES`, `docs/compliance/*`, demo docs as needed.
- [ ] Capture questions/follow-ups without making new product claims.
- [ ] If proposing evaluation/pilot, include governance: consent, training, lawful basis/policy, human accountability, prohibited-use boundaries.
- [ ] Remove any temporary demo artifacts containing sensitive information (if any were created).

## Quick verification commands

```bash
cd /tmp/opencode/cueliez
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 - <<'PY'
from cueliez.packs import get_pack
from cueliez.delivery import OnscreenCueRenderer
t=[{"role":"subject","text":"I think maybe around there, not sure."}]
pkg=get_pack("leg").build_package(t)
print(OnscreenCueRenderer().render_panel(pkg["observations"])["text"])
PY
```
