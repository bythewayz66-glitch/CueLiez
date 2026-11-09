# Note for Grok

Hi Grok — could you please supply **screenshots and videos** for the CueLiez Training GUI?

## Where to add them
Place files in the repo under:

- `docs/training/media/gov/`
- `docs/training/media/leg/`
- `docs/training/media/med/`
- `docs/training/media/thrp/`

## Expected filenames (rendered automatically when present)
Per domain (use the relevant domain folder):

- `overview.png` — module overview (image/screenshot)
- `workflow.png` — workflow screenshot
- `intro.mp4` or `intro.webm` — intro/training video

The GUI already works without these files and shows an honest “No media file provided yet” message until they’re added.

## Content/safety requirements
All media must follow CueLiez language and safety rules (`AGENTS.md`, `docs/LANGUAGE_RULES.md`):

- **Observation/cue-only** framing.
- **No** lie detector / lie detection claims.
- **No** deception, truth, or guilt findings/verdicts.
- **No** clinical diagnoses or medical-device claims.
- **No** polygraph-substitute claims.
- Keep messaging focused on human-led interview support, observed indicators, and probabilistic cues.

## How to verify
Launch the Training GUI and check each module page:

```bash
cd /opt/cueliez
PYTHONPATH=/opt/cueliez/src python3 -m cueliez --training-gui --training-gui-host 127.0.0.1 --training-gui-port 8765
# open http://127.0.0.1:8765/
```

Thanks!
