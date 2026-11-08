# Pilot Validation Metrics (no truth-detection accuracy claims)

**Status:** Measurable operational metrics for first-pilot evaluation (`generic`, `interrogation`).  
**Rule:** Do **not** claim truth-detection accuracy, deception detection rates, confession rates, or automated legal/clinical outcomes. Metrics measure process, integrity, and utility signals only.

## Metrics

| Metric | Definition | How to measure (examples) |
|--------|------------|---------------------------|
| **Latency** | Time from transcript/package input to observations/cues and/or sealed export | Wall-clock per run (CLI/runner timing); report p50/p95 on representative transcripts |
| **Package completeness** | Sealed artifact contains required integrity/process fields | Check `epistemic_status`, `is_definitive_finding`, `disclaimer`/`disclaimer_version`, `gate_state`, `schema_version`, `package_hash`, `observations`; `verify_package_hash` passes |
| **Gate compliance** | Required gates satisfied for mode before seal/start (and recorded in `gate_state`) | Rate of runs blocked by fail-closed `GateError` vs successful gated runs; presence of consent/attester/training/dual-control records where required |
| **Over-cue rate** | Frequency of cues judged low-value/noisy by reviewers on reference transcripts | Human review labels on synthetic/de-identified/authorized transcripts (e.g., owner demos); report counts/qualitative notes, not deception accuracy |
| **Cue utility (qualitative)** | Whether cues supported follow-up questions/review | Structured reviewer feedback; no outcome/accuracy claims |

## Integrity checks (per package)

- `verify_package_hash(package)` is true.
- `epistemic_status == "observed_indicator"`, `is_definitive_finding is False`.
- `gate_state` present with required structure; mode matches session.
- For government/high-priority dual control (when in scope): required `dual_control_records` present.

## Reporting guardrails

- Report **operational** and **process** metrics only.
- Do not compute or publish “accuracy of deception detection” or similar truth-finding metrics.
- Use synthetic, authorized, or de-identified materials for regression/pilot measurement per policy.
