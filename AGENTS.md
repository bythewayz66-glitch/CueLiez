# AGENTS.md — Rules for AI Agents Working on CueLiez

**Product:** CueLiez (Cue + Legal Interview Engine)  
**Core rule:** Observation and cues only. Never lie detection, truth claims, guilt findings, or clinical diagnoses.

This file is mandatory reading for any agent (human or AI) that edits code, docs, UI, tests, marketing copy, or sealed-package logic.

---

## 1. Language Rules (Non-Negotiable)

- Product expansion on first use: **Cue + Legal Interview Engine**.
- Forbidden in all shipped text, comments, UI, packages, and docs:
  - lie detector / detects lies / lie detection
  - truth detector / truth machine / truth score
  - polygraph / polygraph substitute
  - proves deception / confirms lying / the subject is lying
  - guilty / not guilty (as system output)
  - diagnosis (as system output)
  - definitive deception claims

- Required vocabulary:
  - observation / observes / observed indicator
  - signal / indicator / cue
  - inconsistency / conflict in testimony
  - officer assist / interview support
  - probabilistic / confidence-scored
  - sealed observed indicator

- Canonical one-liners (prefer these):
  - "CueLiez observes behavioural and linguistic signals and testimony inconsistencies in real time and presents them to the officer as cues."
  - "CueLiez does not detect lies. It observes actions and patterns around contested accounts so humans can inquire more effectively."
  - "Aimed at making the interview more meaningful for both the guilty and the innocent."

See `docs/LANGUAGE_RULES.md` for the full table. Treat it as law.

---

## 2. Epistemic & Seal Rules

- Every sealed package **must** set:
  - `epistemic_status = "observed_indicator"`
  - `is_definitive_finding = false`
  - `origin = "grounded"` (or equivalent)
  - canonical `disclaimer` text
  - `product = "CueLiez"`
  - `sealed_at` timestamp

- Reject at seal time any observation or annotation that uses verdict language or banned keys (`lying`, `deception_confirmed`, `guilty`, `diagnosis`, `truth_score`, etc.).

- Observations must carry:
  - neutral `label`
  - `confidence.score` in [0.0, 1.0]
  - non-empty `confidence.model_id`
  - method / category / evidence

- Never allow post-seal mutation of observations or epistemic fields through normal APIs.

---

## 3. Gate Rules

- Modes that require affirmative consent + non-empty attester: `interrogation`, `therapy`, `clinical`, `government`.
- Modes that require training acknowledgement + version: same set.
- Dual-control (two distinct officer IDs) required for high-priority cues before seal in `government` mode.
- Prohibited uses (block start or seal): automated detention/charge/clearance, definitive deception claim, clinical diagnosis, medical-device claim, polygraph substitute, covert surveillance without warrant, employment screening without notice, immigration adjudication, child custody determination, lie-detector claim.

Gate state (consent, training, dual-control records, intended uses) must be captured and carried into the sealed package.

---

## 4. Admissibility & Audit Priorities

CueLiez aims to be a **compliance-first interview assist layer**. Goals include both credibility and **admissibility** of the process/record.

Agents must prefer designs that:
- Preserve human judgment as the final step.
- Make the sealed package self-contained, reproducible, and exportable for disclosure/evidence systems.
- Keep consent, training, and dual-control visible in the artifact.
- Support cryptographic hashing/signing of packages (when implementing).
- Avoid any output that could be construed as a scientific finding of truthfulness or deception.

See the Admissibility Requirements Checklist in `TODO.md` / project docs for the full list.

---

## 5. Architecture Constraints

- Observation modules produce probabilistic indicators only.
- Delivery layer (onscreen / audio) surfaces cues to the officer; never automated decisions.
- Domain packs (`gov`, `leg`, `med`, `thrp`) inherit the same language and gate rules; they only change observer sets and guidance text.
- Feature / physiological modalities remain gated and consent-dependent; do not enable by default in packs without explicit policy support.
- Prefer on-prem / private-cloud paths for law-enforcement deployments.

---

## 6. Testing Expectations

- Language tests must fail on any introduction of forbidden terms in core paths.
- Gate tests must cover consent, training, dual-control, prohibited uses, and seal-time rejection of verdict language.
- Observation tests must verify confidence + model_id requirements and neutral labels.
- Seal tests must verify epistemic fields are forced correctly.

---

## 7. Documentation & Marketing

- All external-facing text (README, site, pitch, training) must pass the language checklist.
- Never claim accuracy of deception detection, confession-rate improvement, or automated legal/clinical outcomes.
- Position as: clearer inquiry + auditable record of observations and cues.

---

## 8. When in Doubt

1. Read `docs/LANGUAGE_RULES.md` and `MISSION.md`.
2. Prefer the more restrictive interpretation that protects admissibility and avoids overclaim.
3. Keep the sealed package as an observation artifact, not a finding.
4. Ask for clarification rather than inventing verdict-shaped features.

---

**Last updated from project discussion:** 2026-11-07  
**Primary goal:** Become a standard compliance-first interview-assist layer (credibility + admissibility) that can integrate with Axon, CaseCracker, RMS, and similar systems while remaining strictly observation-and-cue only.
