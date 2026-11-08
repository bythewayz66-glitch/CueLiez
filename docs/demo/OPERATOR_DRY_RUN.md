# CueLiez Operator Dry Run

This is a safe, local dry run using CueLiez transcript fixtures. CueLiez produces **observation cues for human review only** — not findings, diagnoses, or determinations about credibility.

## Prerequisites

From the repository root:

```bash
export PYTHONPATH=src
```

## 1. Preferred owner demo transcripts (reference quality bar)

Use these fully synthetic owner transcripts first (`--mode generic` + `--show-cues`). They are the reference quality bar for the first pilot (`generic` + `interrogation` only). See also `docs/OWNER_DECISIONS.md` §4.

| Transcript | Purpose |
|---|---|
| `docs/examples/owner_clean_interview.json` | Clean cooperative interview |
| `docs/examples/owner_conflict_interview.json` | Interview with conflicting/timeline account details |
| `docs/examples/owner_hedging_interview.json` | Interview with hedging/vague language patterns |

Expected cue counts **after kilo hardening** (observer contract may be in progress; verify current output and coordinate via `agent_notes/` if it differs):
- **owner_clean_interview.json:** 0 cues
- **owner_conflict_interview.json:** ≥1 timeline/consistency cue
- **owner_hedging_interview.json:** several cues

### Copy-paste commands (show cues, generic mode)

```bash
# Clean interview (expected after kilo hardening: 0 cues)
PYTHONPATH=src python -m cueliez docs/examples/owner_clean_interview.json --mode generic --show-cues
```

```bash
# Conflict interview (expected after kilo hardening: >=1 timeline cue)
PYTHONPATH=src python -m cueliez docs/examples/owner_conflict_interview.json --mode generic --show-cues
```

```bash
# Hedging interview (expected after kilo hardening: several cues)
PYTHONPATH=src python -m cueliez docs/examples/owner_hedging_interview.json --mode generic --show-cues
```

For each run:
- Exit code is `0` and the notice line is printed (`CueLiez observes transcript/text signals... does not determine credibility or produce findings`).
- Any displayed cues include source transcript quotes (evidence context) and observation/cue framing only — never findings or verdicts.
- `--no-seal` and sealed paths both work (sealed output includes disclaimer, `gate_state`, `package_hash`, `epistemic_status=observed_indicator`, `is_definitive_finding=false`).

Sealed/export example (owner conflict transcript):

```bash
PYTHONPATH=src python -m cueliez docs/examples/owner_conflict_interview.json \
  --mode generic --show-cues --out-dir ./artifacts/owner-conflict
```

## 2. Minimal smoke example (kept)

For a quick minimal smoke check:

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json --no-seal --show-cues
```

Expected:
- Observation cues are printed (glanceable, priority/turn-linked text).
- Output states cues are for professional review / not findings.
- No forbidden verdict language appears.

## 3. Gated seal + export (non-generic example)

For modes that require gates, provide consent/training flags before observation/seal (CLI uses iceman session lifecycle: `assert_can_observe` / `seal`):

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \
  --mode interrogation \
  --operator-id op-demo \
  --consent --consent-attester op-demo \
  --training-ack \
  --show-cues \
  --out-dir ./artifacts/demo
```

Exports: `sealed_package.json`, `sealed_package.summary.md`, `sealed_package.summary.html` (plus observation cues rendered in output).

## 4. Review page and durable human-readable export

Open `docs/site/index.html` in a browser and go to **Review** (or open `docs/site/review.html`). Load a local `sealed_package.json` export (client-side file input; the page does not claim deployment hosting). Review shows **disclaimer first**, gate/process context, system-observed cues (from package `cues` when present), officer notes (human), and hash/metadata. It must **not** present auto-findings or verdict language.

For human-readable review/attachment, use `sealed_package.summary.md` or `sealed_package.summary.html`. The HTML summary is print/PDF-friendly: open it in a browser and use **Print → Save as PDF** (no additional PDF dependency). Preserve the canonical `sealed_package.json` + `package_hash` as the primary artifact; summaries are observation-only aids, not findings. Source transcript quotes appear in summaries when present.

## 5. Officer notes (before seal only)

Export officer actions from the officer HTML surface as JSON, then attach before sealing:

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json \
  --mode interrogation --operator-id op-demo \
  --consent --consent-attester op-demo \
  --training-ack \
  --officer-notes ./officer_cue_notes.json \
  --out-dir ./out/dry-run-notes
```

Officer notes are human-authored context, not system findings. They must be attached before seal.

## 6. Verify gate refusal (safe check)

A gate-required mode without consent should fail before observation:

```bash
PYTHONPATH=src python -m cueliez docs/examples/sample_transcript.json --mode interrogation --operator-id op-demo
```

Expected: error indicating consent is required (no observation/seal performed).

## Language and safety checks

- All user-visible output should use observation/cue language only.
- No "lie detector", truth/deception verdicts, diagnoses, or automated findings.
- Human judgment remains required.
- For a richer contradiction fixture: `docs/examples/conflict_transcript.json`.