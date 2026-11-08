# Phase 3.5 — Internal Validation Notes (Kilo)

**Scope:** first-pilot modes `generic` + `interrogation` only. Synthetic/de-identified demo transcripts.
**Wording:** observation cues only. **No truth-detection, deception-detection, credibility, guilt, or accuracy claims.**

## Dependency decision (Phase 0)
- No `numpy`/`scipy` (or other signal-feature deps) added to `pyproject.toml`. Current observers are rule/heuristic and do not require them. If future signal features need numeric deps, add only deps actually imported/used and post an agent note.

## Synthetic transcript cue counts (behavior/regression snapshot)
Measured with `default_runner().build_package(...)` on local instance (current build). Counts describe observer behavior on these synthetic examples only; they are **not** accuracy, error-rate, or utility guarantees.

| Transcript | Cues | Categories | Notes (neutral) |
|---|---:|---|---|
| `docs/examples/sample_transcript.json` | 4 | linguistic 3, behavioral 1 | Hedging/vagueness/deflection markers present in synthetic text. |
| `docs/examples/owner_clean_interview.json` | 0 | — | Ordinary routine account; post-hardening hedging/time-approx handling avoids the prior false positive. |
| `docs/examples/owner_conflict_interview.json` | 2 | linguistic 1, consistency 1 | Vagueness marker + multiple spelled-out time references surfaced with source quotes (neutral review cue; not a conflict/deception finding). |
| `docs/examples/owner_hedging_interview.json` | 8 | linguistic 8 | Dense hedging/memory/vagueness language in synthetic text; signals are distinct (no same-phrase duplicates added by hardening). |

## False-positive / over-cue observations (qualitative, internal)
- **Clean baseline:** owner clean transcript produces 0 cues after hardening (time-approximation exclusion for hedging). This is a regression target, not proof of general false-positive rate.
- **Over-cue risk areas:** dense hedging/memory-qualification language can produce multiple cues on the same response/turn when signals are distinct (e.g., hedging + vagueness on different phrases). Reviewers should treat each cue as a prompt for clarification, not a finding.
- **Benign sequences:** timeline/spelled-time logic requires sufficient distinct time references to reduce noise on ordinary short sequential accounts (see `docs/OBSERVER_INVENTORY.md`).

## Officer utility (non-claims)
- Intended utility is **interview support**: surfacing review cues with source quotes for human judgment. Utility has not been validated in field studies here; no operational, confession-rate, or truth-detection claims are made.

## Text cue latency (local estimate)
Measured on local instance (`time.perf_counter`, `default_runner`, text-only): sample/owner transcripts completed in ~**3–7 ms** per package build (small synthetic transcripts). This is well under the **<1–2 s** target for text cues. Real-world latency will depend on transcript size, integration overhead, and deployment environment; re-measure in pilot infrastructure.
