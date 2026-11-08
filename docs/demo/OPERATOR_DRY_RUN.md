# CueLiez Operator Dry Run

This is a safe, local dry run using the sample transcript fixture. CueLiez produces **observation cues for human review only** — not findings, diagnoses, or determinations about credibility.

## Prerequisites

From the repository root:

```bash
export PYTHONPATH=src
```

Fixture transcript (minimal smoke): `docs/examples/sample_transcript.json`
Preferred owner demo transcripts (see `docs/OWNER_DECISIONS.md` §4):
- `docs/examples/owner_clean_interview.json`
- `docs/examples/owner_conflict_interview.json`
- `docs/examples/owner_hedging_interview.json`

## 1. Dry demo (no seal)

Runs observations and renders cues without applying seal/gate state:

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json --no-seal --show-cues
```

Expected:
- Observation cues are printed (glanceable, priority/turn-linked text).
- Output states cues are for professional review / not findings.
- No forbidden verdict language appears.

## 2. Gated seal + export (non-generic example)

For modes that require gates, provide consent/training flags before observation/seal (CLI uses iceman session lifecycle: `assert_can_observe` / `seal`):

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \
  --mode interrogation \
  --consent --consent-attester officer-a \
  --training-version v1 \
  --out-dir ./out/dry-run \
  --basename dry_run
```

Expected:
- Gates are checked before observation in required modes.
- A sealed package is produced with forced `epistemic_status=observed_indicator`, `is_definitive_finding=false`, disclaimer, `gate_state`, and `package_hash` (when iceman seal path is used).
- Exports are written:
  - `./out/dry-run/dry_run.json` (structured package)
  - `./out/dry-run/dry_run.summary.md` (human-readable)
  - `./out/dry-run/dry_run.summary.html` (print/PDF-friendly)

## 3. High-priority cue IDs (dual-control workflow reference)

To display cue IDs that may need dual-control handling in applicable workflows:

```bash
PYTHONPATH=src python -m cueliez docs/examples/conflict_transcript.json \
  --no-seal --list-high-priority
```

(Use `--print-high-priority-cue-ids` as an equivalent alias.)

Glyph displays/exports these IDs only; it does not create dual-control records.

## 4. Officer notes (before seal only)

Export officer actions from the officer HTML surface as JSON, then attach before sealing:

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \
  --mode interrogation --consent --consent-attester officer-a \
  --training-version v1 \
  --officer-notes ./officer_cue_notes.json \
  --out-dir ./out/dry-run-notes
```

Officer notes are human-authored context, not system findings. They must be attached before seal.

## 4b. Owner demo transcripts (hardening pass)

Run each preferred owner transcript in generic mode:

```bash
PYTHONPATH=src python -m cueliez docs/examples/owner_clean_interview.json --mode generic --show-cues
PYTHONPATH=src python -m cueliez docs/examples/owner_conflict_interview.json --mode generic --show-cues
PYTHONPATH=src python -m cueliez docs/examples/owner_hedging_interview.json --mode generic --show-cues
```

Expected after hardening:
- `owner_clean_interview.json`: **0 cues** (no false positives), seals cleanly.
- `owner_conflict_interview.json`: **2 cues** (vague language + multiple time references), with source quotes; seals cleanly.
- `owner_hedging_interview.json`: **8 cues** (hedging/vagueness), neutral wording; seals cleanly.

All three must seal with `epistemic_status=observed_indicator`, `is_definitive_finding=false`, disclaimer, `gate_state`, and `package_hash`.

## 5. Static sealed-package review (optional)

For human review of an exported package JSON, open `docs/site/review.html` in a browser and paste/drop the JSON file. Rendering is client-side only (no upload). Disclaimer appears first; no auto-findings.

## Language and safety checks

- All user-visible output should use observation/cue language only.
- No "lie detector", truth/deception verdicts, diagnoses, or automated findings.
- Human judgment remains required.
