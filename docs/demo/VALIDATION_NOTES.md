# Internal Validation Notes Guidance (CueLiez)

**Purpose:** support Phase 3.5/5 internal validation and pilot learning. This document guides **human** observations of utility and operational behavior. It does **not** define or claim truth-detection accuracy.

## What to record (neutral, non-verdict)

- **Cue utility:** did a cue suggest a reasonable follow-up/clarification question? Was it redundant or distracting?
- **Over-cue / under-cue patterns:** frequency and context of cues on synthetic/approved transcripts (including owner demos). Note possible false-positive patterns as *review observations*, not deception determinations.
- **Source grounding:** were source transcript quotes present and helpful for review when cues appeared?
- **Process/gates:** did consent/training/mode gates behave as expected? Did exports/seals complete with disclaimer, gate state, and hash metadata?
- **Latency (environment-specific):** rough local elapsed time for CLI runs in the operator environment. Report as observed local timing only, not a universal performance guarantee.
- **Package handling:** were JSON/MD/HTML exports understandable and clearly separated into system-observed cues vs officer notes (human)?

## What not to record as claims

Do **not** claim or imply:
- truth-detection accuracy, lie-detection accuracy, or deception-detection rates
- confession-rate improvement attributable to the system
- credibility scores, guilt/innocence determinations, or automated legal/clinical outcomes
- polygraph equivalence or replacement

## Suggested manual commands

```bash
# Owner reference transcripts (first-pilot generic mode)
PYTHONPATH=src python -m cueliez docs/examples/owner_clean_interview.json --mode generic --show-cues --no-seal
PYTHONPATH=src python -m cueliez docs/examples/owner_conflict_interview.json --mode generic --show-cues --no-seal
PYTHONPATH=src python -m cueliez docs/examples/owner_hedging_interview.json --mode generic --show-cues --no-seal

# Optional local timing observation (not a benchmark)
/usr/bin/time -f 'elapsed=%E' PYTHONPATH=src python -m cueliez docs/examples/owner_hedging_interview.json --mode generic --no-seal > /tmp/cueliez_timing.out
```

## Data handling

Use synthetic fixtures or properly authorized/de-identified materials according to policy. Store validation notes and any derived artifacts with appropriate access controls and retention rules. Sealed packages remain observation/cue artifacts, not findings.