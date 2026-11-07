# CueLiez Demo Scenarios (Synthetic / Safe)

Use these **synthetic** examples in demos. Do not use real interview data without authorization, consent, and policy compliance.

## Scenario A — Vagueness, hedging, and assurance language (good for leg/gov)
```python
transcript_a = [
    {"role": "interviewer", "text": "Where were you at 9:00 pm?"},
    {"role": "subject", "text": "I think maybe I was around there, you know, doing stuff somewhere.", "response_latency_ms": 4200},
    {"role": "interviewer", "text": "Can you be specific?"},
    {"role": "subject", "text": "I was at home. I did not go there. I swear, honestly, I never went there.", "response_latency_ms": 900},
    {"role": "interviewer", "text": "Who can confirm that?"},
    {"role": "subject", "text": "Why would you ask that? I already told you.", "response_latency_ms": 1600},
]
```
**Expected cue types (examples):** hedging/low specificity, emphatic negation/assurance language, response latency shift, deflection markers.  
**Demo line:** “These cues suggest where to ask for concrete details or restate a question — not what to conclude.”

## Scenario B — Possible statement conflict (good for leg/gov)
```python
transcript_b = [
    {"role": "interviewer", "text": "Did you enter the store yesterday?"},
    {"role": "subject", "text": "Yes, I entered the store yesterday around noon."},
    {"role": "interviewer", "text": "A record shows no entry. Can you help me understand?"},
    {"role": "subject", "text": "I did not enter the store yesterday."},
    {"role": "interviewer", "text": "What time did you arrive nearby?"},
    {"role": "subject", "text": "I got there at 12:00 pm, maybe 1:30 pm."},
]
```
**Expected cue types:** possible statement conflict, multiple time references/numeric detail cues.  
**Demo line:** “The system flags a possible conflict for reconciliation. The professional presents both accounts neutrally and asks for clarification.”

## Scenario C — Communication clarity/pacing (good for med/thrp)
```python
transcript_c = [
    {"role": "clinician", "text": "Can you walk me through when this started?"},
    {"role": "subject", "text": "Um, I'm not sure exactly... maybe a while ago, if I remember correctly.", "response_latency_ms": 3800},
    {"role": "clinician", "text": "Take your time. Was it days, weeks, or months?"},
    {"role": "subject", "text": "Maybe weeks, I think. It's kind of fuzzy.", "response_latency_ms": 3200},
    {"role": "clinician", "text": "What changed around that time?"},
    {"role": "subject", "text": "Some things, you know."},
]
```
**Expected cue types:** memory qualifiers, hedging, low specificity, latency/pause-related cues (if metadata present).  
**Demo line:** “In a supportive context, these cues can prompt gentle clarification and pacing — never credibility or diagnosis judgments.”

## Scenario D — Multimodal features (only with authorized/consented synthetic feature data)
```python
transcript_d = [
    {"role": "subject", "text": "Yes, that is correct.", "heart_rate_bpm": 72, "gaze_aversion_ratio": 0.12, "pause_total_ms": 250},
    {"role": "subject", "text": "Yes, that is correct.", "heart_rate_bpm": 74, "gaze_aversion_ratio": 0.10, "pause_total_ms": 220},
    {"role": "subject", "text": "Yes, that is correct.", "heart_rate_bpm": 73, "gaze_aversion_ratio": 0.11, "pause_total_ms": 240},
    {"role": "subject", "text": "I think maybe... not exactly.", "heart_rate_bpm": 128, "gaze_aversion_ratio": 0.82, "pause_total_ms": 4200},
]
```
**Demo line:** “Feature adapters can surface shifts from caller-provided, consent-governed measurements as contextual cues. They are not determinations of intent, truthfulness, or medical status.”

## Running a scenario
```python
from cueliez.packs import get_pack
from cueliez.delivery import OnscreenCueRenderer, AudioCueRenderer

pack = get_pack("leg")  # gov/leg/med/thrp
pkg = pack.build_package(transcript_a, session_id="demo-a")
print(OnscreenCueRenderer(show_evidence=True).render_text(
    __import__("cueliez.delivery.events", fromlist=["cues_from_observations"]).cues_from_observations(pkg["observations"]),
    header="CueLiez Demo Cues",
))
AudioCueRenderer(output_dir="demo_audio", allow_playback=False).render_panel(pkg["observations"])
```
